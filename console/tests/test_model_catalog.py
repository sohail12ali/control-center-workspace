"""Provider availability and the model catalogue.

Two subjects, one file, because they are the same question asked twice: **can
this provider be used, and what does it offer?** Both used to have one answer
for several different situations, and that is what made them useless — "not
installed" was the console's reply to a missing binary, an unset key, a server
that was not running, and a row somebody had disabled.

The tests below are mostly about *which* message comes back, not merely that
one does. A wrong-but-plausible reason is worse than none: it sends someone to
install software when the real fix was starting a server they already have.
"""

import json
import os
import socket
import urllib.error

import pytest

from server import agent_backends, model_catalog, openai_client, tomlio

AGENTS_TOML = """\
[[backend]]
id = "cli-one"
label = "A CLI"
command = "definitely-not-a-real-binary-xyz"
transport = "oneshot"
oneshot_args = ["-p", "{prompt}"]

[[backend]]
id = "keyed"
label = "Keyed Provider"
transport = "openai_api"
auth = "key"
api_key_env = "TEST_PROVIDER_KEY"
base_url = "https://provider.example/v1"

[[backend]]
id = "local"
label = "Local Runtime"
transport = "openai_api"
auth = "none"
base_url = "http://127.0.0.1:59999/v1"
start_hint = "Start it with `runtime serve`."

[[backend]]
id = "switched-off"
label = "Off"
transport = "openai_api"
enabled = false
auth = "key"
api_key_env = "TEST_OFF_KEY"
base_url = "https://off.example/v1"
"""


@pytest.fixture
def workspace(repo):
    """A scratch root whose agents.toml exercises every auth mode at once."""
    path = os.path.join(repo, "console", "config", "agents.toml")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(AGENTS_TOML)
    agent_backends._cache.clear()
    agent_backends.forget_probes()
    yield repo
    agent_backends._cache.clear()
    agent_backends.forget_probes()


class Answer:
    """A scripted urlopen. Returns a body, or raises what a real one would.

    Used as a context manager because that is how both callers open it, and a
    stub that only works when called bare would pass tests the real code fails.
    """

    def __init__(self, payload=None, raises=None):
        self.payload = payload
        self.raises = raises
        self.calls = []

    def __call__(self, request, timeout=None):
        self.calls.append(request)
        if self.raises is not None:
            raise self.raises
        return self

    def read(self):
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


# --------------------------------------------------------------- config ----
class TestRowValidation:
    """A misconfigured row must fail at LOAD, next to the file that names it,
    rather than as a mystery 401 on somebody's first turn."""

    def _backend(self, **over):
        row = {"id": "x", "transport": "openai_api", "auth": "key",
               "api_key_env": "K", "base_url": "https://e.example/v1"}
        row.update(over)
        return agent_backends.Backend(row)

    def test_a_keyed_row_without_a_key_env_is_refused(self):
        with pytest.raises(ValueError, match="api_key_env"):
            self._backend(api_key_env=None)

    def test_an_api_row_without_a_base_url_is_refused(self):
        with pytest.raises(ValueError, match="base_url"):
            self._backend(base_url=None)

    def test_an_unknown_auth_mode_is_refused(self):
        with pytest.raises(ValueError, match="unknown auth"):
            self._backend(auth="vibes")

    def test_a_keyless_row_needs_no_key_env(self):
        b = self._backend(auth="none", api_key_env=None)
        assert b.api_key_env == ""

    def test_api_key_env_does_not_fall_back_to_openrouter(self):
        # It used to. A row that forgot the field authenticated against
        # OpenRouter's key while talking to somebody else's base_url — the
        # user's credential sent to a host that was never meant to see it.
        b = self._backend(auth="none", api_key_env=None)
        assert "OPENROUTER" not in b.api_key_env.upper()

    def test_a_cli_row_needs_neither(self):
        b = agent_backends.Backend({"id": "c", "command": "x",
                                    "transport": "oneshot"})
        assert b.auth == "" and b.api_key_env == ""


class TestLocalDetection:
    def test_loopback_is_local(self):
        for url in ("http://127.0.0.1:11434/v1", "http://localhost:1234/v1"):
            b = agent_backends.Backend({"id": "l", "transport": "openai_api",
                                        "auth": "none", "base_url": url})
            assert b.is_local, url

    def test_a_remote_url_is_not(self):
        b = agent_backends.Backend({"id": "r", "transport": "openai_api",
                                    "auth": "key", "api_key_env": "K",
                                    "base_url": "https://api.example/v1"})
        assert not b.is_local

    def test_a_cli_is_never_local(self):
        # "local" is a statement about where the MODEL runs. A CLI runs here
        # too, but it calls out to a provider, so claiming it is local would
        # promise privacy and offline use that it does not have.
        b = agent_backends.Backend({"id": "c", "command": "x",
                                    "transport": "oneshot"})
        assert not b.is_local


class TestModelsUrl:
    def test_it_defaults_to_the_openai_path(self):
        b = agent_backends.Backend({"id": "x", "transport": "openai_api",
                                    "auth": "none",
                                    "base_url": "http://h:1/v1/"})
        assert b.models_url == "http://h:1/v1/models"

    def test_an_explicit_url_wins(self):
        b = agent_backends.Backend({"id": "x", "transport": "openai_api",
                                    "auth": "none", "base_url": "http://h:1/v1",
                                    "models_url": "http://h:1/api/tags"})
        assert b.models_url == "http://h:1/api/tags"


# ---------------------------------------------------------------- probe ----
class TestProbeReasons:
    """Each failure gets its own sentence, because each needs its own fix."""

    def _reason(self, exc, url="http://127.0.0.1:59999/v1/models"):
        return agent_backends._url_error_reason(urllib.error.URLError(exc), url)

    def test_a_dead_loopback_port_says_the_server_is_not_running(self):
        # On Windows a closed loopback port raises TimeoutError, NOT
        # ConnectionRefusedError — verified against 127.0.0.1:11434 with
        # Ollama installed and not serving. Reporting that as "slow" would be
        # true of the socket and useless to the reader.
        assert "nothing is listening" in self._reason(TimeoutError("timed out"))

    def test_a_refused_connection_says_the_same(self):
        assert "nothing is listening" in self._reason(ConnectionRefusedError(111, "refused"))

    def test_an_unresolvable_host_says_check_base_url(self):
        reason = self._reason(socket.gaierror(11001, "getaddrinfo failed"),
                              url="http://nope.invalid/v1/models")
        assert "does not resolve" in reason and "base_url" in reason

    def test_a_slow_remote_host_is_not_called_dead(self):
        # A remote host that is merely slow has not been proven down, and
        # saying it is would send someone restarting a healthy service.
        reason = self._reason(TimeoutError("timed out"),
                              url="https://api.example/v1/models")
        assert "did not answer" in reason
        assert "nothing is listening" not in reason


class TestAvailability:
    def test_a_keyed_provider_needs_its_key(self, workspace, monkeypatch):
        monkeypatch.delenv("TEST_PROVIDER_KEY", raising=False)
        b = agent_backends.get(workspace, "keyed")
        assert not b.installed
        assert "TEST_PROVIDER_KEY" in b.unavailable_reason

    def test_a_keyed_provider_with_its_key_is_available(self, workspace, monkeypatch):
        monkeypatch.setenv("TEST_PROVIDER_KEY", "sk-test")
        assert agent_backends.get(workspace, "keyed").installed

    def test_a_keyless_provider_is_judged_by_reachability(self, workspace, monkeypatch):
        # The bug this whole change exists for: asked whether a key was set, a
        # keyless provider was unavailable forever.
        monkeypatch.setattr(agent_backends, "_probe", lambda *a, **k: (True, ""))
        b = agent_backends.get(workspace, "local")
        assert b.installed

    def test_an_unreachable_keyless_provider_carries_its_start_hint(self, workspace, monkeypatch):
        monkeypatch.setattr(agent_backends, "_probe",
                            lambda *a, **k: (False, "nothing is listening on x"))
        b = agent_backends.get(workspace, "local")
        assert not b.installed
        assert "runtime serve" in b.unavailable_reason

    def test_probes_are_cached(self, monkeypatch):
        # `/api/agents/backends` is polled by the open tab. An uncached probe
        # would be a blocking socket call per provider per poll.
        agent_backends.forget_probes()
        answer = Answer(payload={})
        url = "http://127.0.0.1:59998/v1/models"
        agent_backends._probe(url, opener=answer)
        agent_backends._probe(url, opener=answer)
        assert len(answer.calls) == 1

    def test_a_probe_never_raises(self, monkeypatch):
        agent_backends.forget_probes()

        def boom(*a, **k):
            raise RuntimeError("network is on fire")

        ok, reason = agent_backends._probe("http://127.0.0.1:59997/v1", opener=boom)
        assert ok is False and "RuntimeError" in reason

    def test_an_http_status_still_counts_as_reachable(self):
        # 401 from a gateway means a server answered, which is the question.
        agent_backends.forget_probes()
        err = urllib.error.HTTPError("u", 401, "Unauthorized", {}, None)
        ok, _ = agent_backends._probe("http://127.0.0.1:59996/v1",
                                      opener=Answer(raises=err))
        assert ok is True


class TestDisabledIsNotUnknown:
    def test_a_disabled_row_says_so(self, workspace):
        with pytest.raises(ValueError, match="disabled"):
            agent_backends.get(workspace, "switched-off")

    def test_an_absent_row_says_unknown(self, workspace):
        with pytest.raises(ValueError, match="unknown backend"):
            agent_backends.get(workspace, "no-such-thing")


# ---------------------------------------------------------------- parse ----
OPENROUTER_BODY = {"data": [
    {"id": "z/model", "name": "Zed", "context_length": 131072,
     "pricing": {"prompt": "0.0000008", "completion": "0.0000016"}},
    {"id": "a/model", "name": "Aye", "top_provider": {"context_length": 8192},
     "pricing": {"prompt": "0", "completion": "0"}},
]}


class TestParse:
    def test_prices_become_per_million_tokens(self):
        rows = {r["id"]: r for r in model_catalog.parse(OPENROUTER_BODY)}
        # 0.0000008/token is 0.80/Mtok — and it must not arrive as
        # 0.7999999999999999, which is what the bare multiply produced.
        assert rows["z/model"]["input_per_mtok"] == 0.8
        assert rows["z/model"]["output_per_mtok"] == 1.6

    def test_context_is_read_from_either_place(self):
        rows = {r["id"]: r for r in model_catalog.parse(OPENROUTER_BODY)}
        assert rows["z/model"]["context"] == 131072
        assert rows["a/model"]["context"] == 8192   # from top_provider

    def test_rows_come_back_sorted_by_id(self):
        assert [r["id"] for r in model_catalog.parse(OPENROUTER_BODY)] == \
            ["a/model", "z/model"]

    def test_a_model_with_no_pricing_carries_none(self):
        # Ollama reports no prices. Absent must stay absent all the way to the
        # UI, where it renders as "unpriced" — never as $0.00, which reads as
        # free and is the one lie the spend panel must not tell.
        rows = model_catalog.parse({"data": [{"id": "llama3.1:8b"}]})
        assert "input_per_mtok" not in rows[0]
        assert "output_per_mtok" not in rows[0]

    def test_an_unparseable_price_is_dropped_not_zeroed(self):
        rows = model_catalog.parse(
            {"data": [{"id": "m", "pricing": {"prompt": "free", "completion": None}}]})
        assert "input_per_mtok" not in rows[0]

    def test_a_bare_list_is_accepted(self):
        assert model_catalog.parse([{"id": "m"}])[0]["id"] == "m"

    def test_junk_entries_are_skipped_not_fatal(self):
        rows = model_catalog.parse({"data": ["nonsense", {}, {"id": "ok"}]})
        assert [r["id"] for r in rows] == ["ok"]

    def test_an_unexpected_shape_yields_nothing_rather_than_raising(self):
        assert model_catalog.parse({"models": ["a"]}) == []

    def test_the_label_falls_back_to_the_id(self):
        assert model_catalog.parse({"data": [{"id": "m"}]})[0]["label"] == "m"


# ---------------------------------------------------------------- fetch ----
class TestFetch:
    def test_a_successful_fetch_caches_to_disk(self, workspace, monkeypatch):
        monkeypatch.setenv("TEST_PROVIDER_KEY", "sk-test")
        rows, error = model_catalog.fetch(workspace, "keyed",
                                          opener=Answer(OPENROUTER_BODY))
        assert error == "" and len(rows) == 2
        path = model_catalog.cache_path(workspace, "keyed")
        assert os.path.isfile(path)
        assert tomlio.load(path)["count"] == 2

    def test_the_cache_round_trips(self, workspace, monkeypatch):
        monkeypatch.setenv("TEST_PROVIDER_KEY", "sk-test")
        model_catalog.fetch(workspace, "keyed", opener=Answer(OPENROUTER_BODY))
        hit = model_catalog.cached(workspace, "keyed")
        assert hit["count"] == 2
        assert {m["id"] for m in hit["models"]} == {"a/model", "z/model"}
        assert hit["age_days"] is not None

    def test_the_key_is_sent_as_a_header_and_never_in_the_url(self, workspace, monkeypatch):
        monkeypatch.setenv("TEST_PROVIDER_KEY", "sk-secret")
        answer = Answer(OPENROUTER_BODY)
        model_catalog.fetch(workspace, "keyed", opener=answer)
        request = answer.calls[0]
        assert "sk-secret" not in request.full_url
        assert request.headers["Authorization"] == "Bearer sk-secret"

    def test_a_keyless_provider_sends_no_authorization(self, workspace, monkeypatch):
        monkeypatch.setattr(agent_backends, "_probe", lambda *a, **k: (True, ""))
        answer = Answer({"data": [{"id": "llama3.1:8b"}]})
        rows, error = model_catalog.fetch(workspace, "local", opener=answer)
        assert error == "" and len(rows) == 1
        assert "Authorization" not in answer.calls[0].headers

    def test_a_missing_key_is_reported_before_any_call(self, workspace, monkeypatch):
        monkeypatch.delenv("TEST_PROVIDER_KEY", raising=False)
        answer = Answer(OPENROUTER_BODY)
        rows, error = model_catalog.fetch(workspace, "keyed", opener=answer)
        assert rows == [] and "TEST_PROVIDER_KEY" in error
        assert answer.calls == []   # nothing left the machine

    def test_rejected_credentials_say_so(self, workspace, monkeypatch):
        monkeypatch.setenv("TEST_PROVIDER_KEY", "sk-bad")
        err = urllib.error.HTTPError("u", 401, "Unauthorized", {}, None)
        _rows, error = model_catalog.fetch(workspace, "keyed",
                                           opener=Answer(raises=err))
        assert "rejected the credentials" in error

    def test_the_error_never_contains_the_key(self, workspace, monkeypatch):
        monkeypatch.setenv("TEST_PROVIDER_KEY", "sk-super-secret")
        err = urllib.error.HTTPError("u", 500, "Server Error", {}, None)
        _rows, error = model_catalog.fetch(workspace, "keyed",
                                           opener=Answer(raises=err))
        assert "sk-super-secret" not in error

    def test_an_unreachable_provider_is_reported_not_raised(self, workspace, monkeypatch):
        monkeypatch.setattr(agent_backends, "_probe", lambda *a, **k: (True, ""))
        exc = urllib.error.URLError(ConnectionRefusedError(111, "refused"))
        rows, error = model_catalog.fetch(workspace, "local",
                                          opener=Answer(raises=exc))
        assert rows == [] and "nothing is listening" in error

    def test_a_non_json_answer_is_reported_not_raised(self, workspace, monkeypatch):
        monkeypatch.setenv("TEST_PROVIDER_KEY", "sk-test")

        class Html(Answer):
            def read(self):
                return b"<html>gateway</html>"

        rows, error = model_catalog.fetch(workspace, "keyed", opener=Html({}))
        assert rows == [] and "not JSON" in error

    def test_an_empty_catalogue_explains_itself(self, workspace, monkeypatch):
        # Ollama running with nothing pulled answers 200 with an empty list.
        # Verified against a real server on 2026-08-29.
        monkeypatch.setattr(agent_backends, "_probe", lambda *a, **k: (True, ""))
        rows, error = model_catalog.fetch(workspace, "local",
                                          opener=Answer({"data": []}))
        assert rows == [] and "nothing is pulled or loaded" in error

    def test_a_cli_backend_is_refused_with_a_useful_reason(self, workspace):
        _rows, error = model_catalog.fetch(workspace, "cli-one")
        assert "is a CLI" in error and "agents.toml" in error

    def test_a_disabled_backend_says_disabled(self, workspace):
        _rows, error = model_catalog.fetch(workspace, "switched-off")
        assert "disabled" in error

    def test_the_model_cap_is_enforced(self, workspace, monkeypatch):
        monkeypatch.setenv("TEST_PROVIDER_KEY", "sk-test")
        huge = {"data": [{"id": "m%05d" % i}
                         for i in range(model_catalog.MAX_MODELS + 500)]}
        rows, _error = model_catalog.fetch(workspace, "keyed", opener=Answer(huge))
        assert len(rows) == model_catalog.MAX_MODELS


class TestCacheReading:
    def test_no_cache_reads_as_none(self, workspace):
        assert model_catalog.cached(workspace, "keyed") is None

    def test_a_corrupt_cache_reads_as_none_rather_than_raising(self, workspace):
        path = model_catalog.cache_path(workspace, "keyed")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("this is not = [valid toml\n")
        assert model_catalog.cached(workspace, "keyed") is None

    def test_a_backend_id_cannot_escape_the_cache_directory(self, workspace):
        # Ids come from config, so this is defence in depth rather than a
        # live attack — but a path built from data is a path worth checking.
        for bad in ("../../etc/passwd", "a/b", "a\\b"):
            with pytest.raises(ValueError):
                model_catalog.cache_path(workspace, bad)

    def test_summary_covers_api_providers_only(self, workspace, monkeypatch):
        monkeypatch.setattr(agent_backends, "_probe", lambda *a, **k: (True, ""))
        ids = {row["id"] for row in model_catalog.summary(workspace)}
        assert "cli-one" not in ids        # a CLI has no catalogue to summarise
        assert {"keyed", "local"} <= ids
        assert "switched-off" not in ids   # disabled rows are not offered


class TestKeylessClient:
    def test_a_keyless_client_sends_no_authorization_header(self):
        client = openai_client.Client(base_url="http://127.0.0.1:1234/v1",
                                      api_key_env="")
        assert client.keyless
        assert "Authorization" not in client._headers()

    def test_a_keyless_client_reports_itself_usable(self, monkeypatch):
        # `has_key` gates the composer. For a provider with no key, "no key"
        # must not read as "not configured".
        client = openai_client.Client(base_url="http://127.0.0.1:1234/v1",
                                      api_key_env="")
        assert client.has_key is True

    def test_a_keyed_client_still_demands_its_key(self, monkeypatch):
        monkeypatch.delenv("TEST_K", raising=False)
        client = openai_client.Client(base_url="https://e.example/v1",
                                      api_key_env="TEST_K")
        assert client.has_key is False
        with pytest.raises(openai_client.ApiError, match="TEST_K"):
            client._headers()
