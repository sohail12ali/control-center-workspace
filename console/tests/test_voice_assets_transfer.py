"""The transfer core (T-031-07; AC-13, 15, 17, 25) and, below it, retry and URL
policy (T-031-08; AC-14, 16, 31).

Every test talks to the local range server in `voice_assets_server.py` on
127.0.0.1: no real network, no process spawned, and `sleep` is injected so the
suite never waits on backoff.
"""

import os
import tracemalloc
import urllib.error

import pytest

from voice_assets_server import Body, GeneratedBody, RangeServer
from server import voice_assets
from server.voice_assets import AssetFile, Interrupted, Transfer, TransferError

NAME = "ggml-test.bin"
PATH = "/models/" + NAME


def make_body(size, seed=7):
    import random
    return Body(random.Random(seed).randbytes(size))


def spec_for(server, body, size=None, name=NAME, path=PATH):
    return AssetFile(name=name, url=server.url(path),
                     size=body.size if size is None else size,
                     sha256=body.sha256(), hash_source="hf-lfs-oid")


def make_transfer(spec, dest, sleeps=None, **kwargs):
    """The one place a test builds a Transfer: loopback http is admitted (the
    local server is http) and `sleep` records instead of sleeping, so the suite
    never waits on backoff. A test that wants the real policy passes
    `allow_loopback_http=False`."""
    kwargs.setdefault("allow_loopback_http", True)
    kwargs.setdefault("sleep", (sleeps if sleeps is not None else []).append)
    return Transfer(spec, str(dest), **kwargs)


def read(path):
    with open(path, "rb") as fh:
        return fh.read()


@pytest.fixture
def dest(tmp_path):
    return tmp_path / "stt"


# --- AC-13: Range resume ----------------------------------------------------

def test_a_fresh_start_sends_no_range_header_and_the_bytes_are_correct(dest):
    body = make_body(2_500_000)           # more than two 1 MiB chunks
    with RangeServer({PATH: body}) as server:
        transfer = make_transfer(spec_for(server, body), dest)
        part = transfer.run()
    assert part == str(dest / (NAME + ".part"))
    assert read(part) == body.data
    assert [r["range"] for r in server.gets()] == [None]
    assert transfer.resumed_from == 0


def test_resume_sends_range_equal_to_the_part_size_and_the_bytes_are_correct(dest):
    body = make_body(3_000_000)
    dest.mkdir()
    (dest / (NAME + ".part")).write_bytes(body.data[:1_234_567])
    with RangeServer({PATH: body}) as server:
        transfer = make_transfer(spec_for(server, body), dest)
        part = transfer.run()
    assert [r["range"] for r in server.gets()] == ["bytes=1234567-"]
    assert read(part) == body.data
    assert transfer.resumed_from == 1_234_567


def test_a_connection_that_closes_early_keeps_the_part_and_the_next_run_resumes(dest):
    body = make_body(2_000_000)
    dest.mkdir()                            # `run()` makes it; `_attempt` does not
    with RangeServer({PATH: body}, drop_after=[700_000]) as server:
        first = make_transfer(spec_for(server, body), dest)
        with pytest.raises(TransferError) as caught:
            first._attempt(0)               # one connection, no retry loop
        assert caught.value.retryable
        assert first.have() == 700_000
        second = make_transfer(spec_for(server, body), dest)
        part = second.run()
    assert [r["range"] for r in server.gets()] == [None, "bytes=700000-"]
    assert read(part) == body.data


# --- AC-15, 416 -------------------------------------------------------------

def test_a_200_reply_to_a_range_request_restarts_from_zero(dest):
    body = make_body(2_200_000)
    dest.mkdir()
    (dest / (NAME + ".part")).write_bytes(b"stale-prefix-that-must-not-survive" * 1000)
    with RangeServer({PATH: body}, ignore_range=True) as server:
        part = make_transfer(spec_for(server, body), dest).run()
    assert server.gets()[0]["range"] is not None, "a Range request was sent"
    assert read(part) == body.data, "the stale prefix was not kept"


def test_416_at_full_size_means_complete(dest):
    body = make_body(5000)
    dest.mkdir()
    (dest / (NAME + ".part")).write_bytes(body.data)
    spec = AssetFile(name=NAME, url="http://127.0.0.1:9/never-contacted", size=5000,
                     sha256=body.sha256(), hash_source="hf-lfs-oid")
    err = urllib.error.HTTPError(spec.url, 416, "Range Not Satisfiable", {}, None)

    def refuse_with_416(request, timeout):
        raise err

    transfer = make_transfer(spec, dest, opener=refuse_with_416)
    assert transfer._attempt(5000) is True
    assert read(transfer.part) == body.data, "a complete part is left alone"


def test_416_below_full_size_deletes_the_part_and_restarts(dest):
    body = make_body(300_000)
    dest.mkdir()
    (dest / (NAME + ".part")).write_bytes(body.data[:100_000])
    with RangeServer({PATH: body}, status_script=[416]) as server:
        part = make_transfer(spec_for(server, body), dest).run()
    assert [r["range"] for r in server.gets()] == ["bytes=100000-", None]
    assert read(part) == body.data


# --- AC-17: the upstream file changed ----------------------------------------

def test_a_content_range_total_that_differs_from_the_catalog_fails_and_removes_the_part(dest):
    body = make_body(400_000)
    dest.mkdir()
    (dest / (NAME + ".part")).write_bytes(body.data[:50_000])
    with RangeServer({PATH: body}, wrong_total=body.size + 1) as server:
        transfer = make_transfer(spec_for(server, body), dest)
        with pytest.raises(TransferError) as caught:
            transfer.run()
    assert "upstream file changed" in str(caught.value)
    assert not caught.value.retryable
    assert not os.path.exists(transfer.part)


def test_a_response_size_that_differs_from_the_catalog_fails_and_removes_the_part(dest):
    body = make_body(400_000)
    with RangeServer({PATH: body}) as server:
        transfer = make_transfer(spec_for(server, body, size=body.size + 5), dest)
        with pytest.raises(TransferError) as caught:
            transfer.run()
    assert "upstream file changed" in str(caught.value)
    assert not os.path.exists(transfer.part)
    assert not os.path.exists(transfer.final)


def test_a_part_larger_than_the_catalog_size_is_discarded_and_restarted(dest):
    body = make_body(100_000)
    dest.mkdir()
    (dest / (NAME + ".part")).write_bytes(b"x" * 150_000)
    with RangeServer({PATH: body}) as server:
        part = make_transfer(spec_for(server, body), dest).run()
    assert [r["range"] for r in server.gets()] == [None]
    assert read(part) == body.data


# --- a zero-byte reply is a failure, not an install ---------------------------

def test_a_zero_byte_reply_is_a_failure_and_leaves_nothing_behind(dest):
    body = make_body(50_000)
    with RangeServer({PATH: body}, drop_after=[0] * 10) as server:
        transfer = make_transfer(spec_for(server, body), dest)
        with pytest.raises(TransferError) as caught:
            transfer.run()
    assert "no data" in str(caught.value)
    assert not os.path.exists(transfer.part) and not os.path.exists(transfer.final)


def test_an_empty_body_for_a_catalog_file_that_has_size_is_a_failure(dest):
    with RangeServer({PATH: Body(b"")}) as server:
        spec = AssetFile(name=NAME, url=server.url(PATH), size=1000,
                         sha256="a" * 64, hash_source="hf-lfs-oid")
        transfer = make_transfer(spec, dest)
        with pytest.raises(TransferError):
            transfer.run()
    assert not os.path.exists(transfer.final)


# --- AC-25: streaming, never buffering ----------------------------------------

def test_32_mib_streams_with_under_8_mib_of_python_allocations(dest):
    body = GeneratedBody(32 * 1024 * 1024)
    expected = body.sha256()
    with RangeServer({PATH: body}) as server:
        transfer = make_transfer(spec_for(server, body), dest)
        tracemalloc.start()
        try:
            part = transfer.run()
            _current, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
    assert os.path.getsize(part) == body.size
    import hashlib
    digest = hashlib.sha256()
    with open(part, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            digest.update(block)
    assert digest.hexdigest() == expected
    assert peak < 8 * 1024 * 1024, "peak %d bytes: the transfer buffers" % peak


# --- the seams jobs build on --------------------------------------------------

def test_progress_is_reported_per_chunk_and_never_goes_backwards(dest):
    body = make_body(3_500_000)
    seen = []
    with RangeServer({PATH: body}) as server:
        make_transfer(spec_for(server, body), dest, on_progress=seen.append).run()
    assert seen == sorted(seen) and seen[-1] == body.size and len(seen) >= 3


def test_a_stop_request_ends_the_transfer_between_chunks_and_keeps_the_part(dest):
    body = make_body(3_500_000)
    seen = []
    with RangeServer({PATH: body}) as server:
        transfer = make_transfer(
            spec_for(server, body), dest, on_progress=seen.append,
            stop=lambda: "pause" if seen else None)
        with pytest.raises(Interrupted) as caught:
            transfer.run()
    assert caught.value.reason == "pause"
    assert 0 < transfer.have() < body.size


# ===========================================================================
# T-031-08: retry, backoff, URL policy
# ===========================================================================

from server.voice_assets import PolicyError, backoff_delay   # noqa: E402


# --- AC-14, AC-16: backoff and retry ------------------------------------------

def test_the_backoff_delay_table_is_half_a_second_doubling_capped_at_sixteen():
    assert [backoff_delay(n) for n in range(7)] == [0.5, 1, 2, 4, 8, 16, 16]
    assert backoff_delay(50) == 16


def test_six_failures_then_success_sleeps_1_2_4_8_16_16(dest):
    body = make_body(100_000)
    sleeps = []
    with RangeServer({PATH: body}, status_script=[503] * 6) as server:
        part = make_transfer(spec_for(server, body), dest, sleeps=sleeps).run()
    assert sleeps == [1, 2, 4, 8, 16, 16]
    assert read(part) == body.data
    assert len(server.gets()) == 7


def test_the_seventh_consecutive_failure_fails_keeps_the_part_and_a_second_run_resumes(dest):
    body = make_body(400_000)
    dest.mkdir()
    (dest / (NAME + ".part")).write_bytes(body.data[:90_000])
    sleeps = []
    with RangeServer({PATH: body}, status_script=[503] * 7) as server:
        spec = spec_for(server, body)
        first = make_transfer(spec, dest, sleeps=sleeps)
        with pytest.raises(TransferError) as caught:
            first.run()
        assert "giving up" in str(caught.value) and "503" in str(caught.value)
        assert sleeps == [1, 2, 4, 8, 16, 16], "six sleeps, then the seventh fails"
        assert len(server.gets()) == 7
        assert first.have() == 90_000, "the part survives a give-up"
        second = make_transfer(spec, dest)
        part = second.run()
    assert server.gets()[-1]["range"] == "bytes=90000-"
    assert second.resumed_from == 90_000
    assert read(part) == body.data


def test_more_than_six_mid_body_drops_that_each_deliver_bytes_still_succeed(dest):
    body = make_body(2_000_000)
    sleeps = []
    with RangeServer({PATH: body}, drop_after=[200_000] * 8) as server:
        part = make_transfer(spec_for(server, body), dest, sleeps=sleeps).run()
    assert read(part) == body.data
    assert sleeps == [1] * 8, "bytes arriving reset the counter every time"
    ranges = [r["range"] for r in server.gets()]
    assert ranges[0] is None and ranges[1] == "bytes=200000-" and ranges[2] == "bytes=400000-"


@pytest.mark.parametrize("code", [404, 403])
def test_a_4xx_other_than_429_fails_at_once_with_no_sleep(dest, code):
    body = make_body(10_000)
    sleeps = []
    with RangeServer({PATH: body}, status_script=[code]) as server:
        with pytest.raises(TransferError) as caught:
            make_transfer(spec_for(server, body), dest, sleeps=sleeps).run()
    assert str(code) in str(caught.value) and not caught.value.retryable
    assert sleeps == [] and len(server.gets()) == 1


@pytest.mark.parametrize("code", [429, 503])
def test_429_and_503_are_retried(dest, code):
    body = make_body(10_000)
    sleeps = []
    with RangeServer({PATH: body}, status_script=[code]) as server:
        part = make_transfer(spec_for(server, body), dest, sleeps=sleeps).run()
    assert sleeps == [1] and len(server.gets()) == 2
    assert read(part) == body.data


def test_a_refused_connection_is_retried_then_gives_up(dest):
    calls, sleeps = [], []

    def refuse(request, timeout):
        calls.append(request.full_url)
        raise urllib.error.URLError(ConnectionRefusedError("refused"))

    spec = AssetFile(name=NAME, url="http://127.0.0.1:9/x", size=10, sha256="a" * 64,
                     hash_source="hf-lfs-oid")
    with pytest.raises(TransferError) as caught:
        make_transfer(spec, dest, sleeps=sleeps, opener=refuse).run()
    assert "giving up" in str(caught.value) and "cannot reach" in str(caught.value)
    assert sleeps == [1, 2, 4, 8, 16, 16] and len(calls) == 7


def test_on_retry_is_told_before_every_wait(dest):
    body = make_body(10_000)
    told = []
    with RangeServer({PATH: body}, status_script=[503, 503]) as server:
        make_transfer(spec_for(server, body), dest,
                      on_retry=lambda n, delay, msg: told.append((n, delay))).run()
    assert told == [(1, 1), (2, 2)]


def test_a_cancel_during_a_backoff_wait_ends_the_transfer(dest):
    body = make_body(10_000)
    state = {"retried": False}
    with RangeServer({PATH: body}, status_script=[503] * 3) as server:
        transfer = make_transfer(
            spec_for(server, body), dest,
            on_retry=lambda *a: state.update(retried=True),
            stop=lambda: "cancel" if state["retried"] else None)
        with pytest.raises(Interrupted) as caught:
            transfer.run()
    assert caught.value.reason == "cancel" and len(server.gets()) == 1


def test_a_server_that_keeps_answering_416_does_not_loop_forever(dest):
    body = make_body(10_000)
    with RangeServer({PATH: body}, status_script=[416] * 9) as server:
        with pytest.raises(TransferError) as caught:
            make_transfer(spec_for(server, body), dest).run()
    assert "refusing to resume" in str(caught.value)
    assert len(server.gets()) == 3


# --- AC-31: URL policy --------------------------------------------------------

class FakeResponse:
    """Just enough of an HTTP response for the injected-opener tests."""

    def __init__(self, data, url=None, status=200):
        import io
        self._io = io.BytesIO(data)
        self.status = status
        self.headers = {"Content-Length": str(len(data))}
        self._url = url
        self.closed = False

    def read(self, n=-1):
        return self._io.read(n)

    def close(self):
        self.closed = True

    def geturl(self):
        return self._url


class RecordingOpener:
    def __init__(self, response=None):
        self.requests = []
        self.response = response

    def __call__(self, request, timeout):
        self.requests.append(request)
        return self.response


def policy_spec(url, size=10):
    return AssetFile(name=NAME, url=url, size=size, sha256="a" * 64,
                     hash_source="hf-lfs-oid")


def test_a_non_loopback_http_url_is_refused_before_any_connection(dest):
    opener = RecordingOpener(FakeResponse(b"x" * 10))
    for flag in (False, True):          # the test-only flag admits 127.0.0.1 only
        transfer = make_transfer(policy_spec("http://example.com/" + NAME), dest,
                                 opener=opener, allow_loopback_http=flag)
        with pytest.raises(PolicyError) as caught:
            transfer.run()
        assert "https" in str(caught.value) and not caught.value.retryable
    assert opener.requests == [], "the policy runs ahead of the connection"


@pytest.mark.parametrize("url", [
    "https://evil.example/x.bin",
    "https://huggingface.co.evil.example/x.bin",       # look-alike suffix
    "https://evilhuggingface.co/x.bin",                # look-alike prefix
    "https://huggingface.co@evil.example/x.bin",       # userinfo trick
    "https://user:secret@huggingface.co/x.bin",        # credentials
    "https://huggingface.co:8443/x.bin",               # not the https port
    "ftp://huggingface.co/x.bin",
    "file:///etc/passwd",
])
def test_a_foreign_or_lookalike_initial_host_is_refused_even_with_a_fake_opener(dest, url):
    opener = RecordingOpener(FakeResponse(b"x" * 10))
    with pytest.raises(PolicyError):
        make_transfer(policy_spec(url), dest, opener=opener,
                      allow_loopback_http=True).run()
    assert opener.requests == []


def test_the_pinned_host_is_accepted_and_the_request_carries_no_credentials(dest):
    opener = RecordingOpener(FakeResponse(b"x" * 10))
    transfer = make_transfer(policy_spec("https://huggingface.co/a/b/resolve/" + "a" * 40 + "/x.bin"),
                             dest, opener=opener, allow_loopback_http=False)
    assert read(transfer.run()) == b"x" * 10
    headers = {k.lower() for k in opener.requests[0].headers}
    assert not headers & {"authorization", "cookie", "proxy-authorization"}


def test_credentials_added_to_a_request_are_stripped_before_it_is_sent(dest):
    opener = RecordingOpener(FakeResponse(b"x" * 10))
    transfer = make_transfer(policy_spec("https://huggingface.co/x.bin"), dest, opener=opener)
    request = urllib_request_with_credentials("https://huggingface.co/x.bin")
    transfer._open(request)
    assert {k.lower() for k in opener.requests[0].headers} == {"accept"}


def urllib_request_with_credentials(url):
    import urllib.request
    return urllib.request.Request(url, headers={
        "Authorization": "Bearer hf_secret", "Cookie": "session=1",
        "Proxy-Authorization": "Basic abc", "Accept": "*/*"})


def test_the_local_server_sees_no_authorization_or_cookie_header(dest):
    body = make_body(50_000)
    with RangeServer({PATH: body}) as server:
        make_transfer(spec_for(server, body), dest).run()
    for record in server.requests:
        assert not set(record["headers"]) & {"authorization", "cookie", "proxy-authorization"}


def test_an_http_redirect_target_is_refused(dest):
    body = make_body(10_000)
    with RangeServer({PATH: body}, redirect_to="http://evil.example/steal.bin") as server:
        transfer = make_transfer(spec_for(server, body), dest)
        with pytest.raises(PolicyError) as caught:
            transfer.run()
    assert "https" in str(caught.value) and not caught.value.retryable
    assert len(server.requests) == 1, "the redirect was never followed"
    assert not os.path.exists(transfer.part)


def test_a_redirect_to_an_allowed_target_is_followed_and_the_bytes_arrive(dest):
    body = make_body(300_000)
    with RangeServer({PATH: body}) as origin, RangeServer({"/cdn/file": body}) as cdn:
        origin.redirect_to = cdn.url("/cdn/file")       # loopback http only in test mode
        part = make_transfer(spec_for(origin, body), dest).run()
    assert read(part) == body.data
    assert len(cdn.gets()) == 1


def test_the_redirect_handler_allows_any_https_host_and_drops_credentials():
    from server.voice_assets import _PolicyRedirectHandler
    import urllib.request
    handler = _PolicyRedirectHandler(allow_loopback_http=False)
    original = urllib_request_with_credentials("https://huggingface.co/x.bin")
    followed = handler.redirect_request(original, None, 302, "Found", {},
                                        "https://cas-bridge.cdn.example/blob")
    assert followed.full_url == "https://cas-bridge.cdn.example/blob"
    assert not {k.lower() for k in followed.headers} & {"authorization", "cookie"}
    for bad in ("http://cdn.example/blob", "https://u:p@cdn.example/blob", "ftp://cdn.example/b"):
        with pytest.raises(PolicyError):
            handler.redirect_request(original, None, 302, "Found", {}, bad)


def test_the_final_url_of_an_answer_is_checked_even_with_a_fake_opener(dest):
    response = FakeResponse(b"x" * 10, url="http://evil.example/steal.bin")
    opener = RecordingOpener(response)
    with pytest.raises(PolicyError):
        make_transfer(policy_spec("https://huggingface.co/x.bin"), dest, opener=opener).run()
    assert response.closed, "the refused answer's connection is closed"
