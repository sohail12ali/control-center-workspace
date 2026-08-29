"""Streaming client.

Streaming bugs of this kind truncate answers rather than crashing, so they
survive casual use and surface later as "the model seems worse on this
backend". Every awkward shape the wire actually produces is pinned here with
fixture text and no network.
"""

import io
import json
import urllib.error

import pytest

from server import openai_client as oc


def sse(*chunks, done=True):
    """Fixture stream in the wire's own format."""
    lines = ["data: " + json.dumps(c) for c in chunks]
    if done:
        lines.append("data: [DONE]")
    return io.StringIO("\n\n".join(lines) + "\n")


def text_chunk(text):
    return {"choices": [{"delta": {"content": text}}]}


class TestParseSse:
    def test_yields_json_objects(self):
        assert list(oc.parse_sse(sse({"a": 1}, {"b": 2}))) == [{"a": 1}, {"b": 2}]

    def test_stops_at_done(self):
        stream = io.StringIO('data: {"a":1}\ndata: [DONE]\ndata: {"b":2}\n')
        assert list(oc.parse_sse(stream)) == [{"a": 1}]

    def test_ignores_comments_and_blank_lines(self):
        stream = io.StringIO(': keep-alive\n\n\ndata: {"a":1}\n\n')
        assert list(oc.parse_sse(stream)) == [{"a": 1}]

    def test_a_malformed_line_does_not_truncate_the_stream(self):
        # One bad keep-alive must not cost the rest of the reply.
        stream = io.StringIO('data: {"a":1}\ndata: not json\ndata: {"b":2}\n')
        assert list(oc.parse_sse(stream)) == [{"a": 1}, {"b": 2}]

    def test_a_final_chunk_without_a_newline_is_still_read(self):
        stream = io.StringIO('data: {"a":1}')
        assert list(oc.parse_sse(stream)) == [{"a": 1}]

    def test_bytes_streams_work_too(self):
        stream = [b'data: {"a":1}\n', b"data: [DONE]\n"]
        assert list(oc.parse_sse(stream)) == [{"a": 1}]

    def test_non_data_lines_are_skipped(self):
        stream = io.StringIO('event: message\ndata: {"a":1}\n')
        assert list(oc.parse_sse(stream)) == [{"a": 1}]


class TestAccumulator:
    def test_text_deltas_concatenate(self):
        acc = oc.Accumulator()
        deltas = [acc.feed(text_chunk(t)) for t in ("Hel", "lo ", "world")]
        assert deltas == ["Hel", "lo ", "world"]
        assert acc.finish().content == "Hello world"

    def test_reasoning_is_kept_separate_from_content(self):
        acc = oc.Accumulator()
        acc.feed({"choices": [{"delta": {"reasoning": "thinking..."}}]})
        acc.feed(text_chunk("answer"))
        result = acc.finish()
        assert result.content == "answer"
        assert result.reasoning == "thinking..."

    def test_a_tool_call_split_across_chunks_is_reassembled(self):
        # The wire form: name and id once, arguments as fragments.
        acc = oc.Accumulator()
        acc.feed({"choices": [{"delta": {"tool_calls": [
            {"index": 0, "id": "call_1",
             "function": {"name": "read_file", "arguments": '{"pa'}}]}}]})
        acc.feed({"choices": [{"delta": {"tool_calls": [
            {"index": 0, "function": {"arguments": 'th":"a.py"}'}}]}}]})
        call = acc.finish().tool_calls[0]
        assert (call.id, call.name) == ("call_1", "read_file")
        assert call.arguments == {"path": "a.py"}

    def test_parallel_tool_calls_are_kept_apart_by_index(self):
        acc = oc.Accumulator()
        acc.feed({"choices": [{"delta": {"tool_calls": [
            {"index": 0, "id": "a", "function": {"name": "read_file", "arguments": "{}"}},
            {"index": 1, "id": "b", "function": {"name": "list_files", "arguments": "{}"}},
        ]}}]})
        calls = acc.finish().tool_calls
        assert [c.name for c in calls] == ["read_file", "list_files"]

    def test_interleaved_fragments_land_on_the_right_call(self):
        acc = oc.Accumulator()
        acc.feed({"choices": [{"delta": {"tool_calls": [
            {"index": 0, "id": "a", "function": {"name": "x", "arguments": '{"p":"'}}]}}]})
        acc.feed({"choices": [{"delta": {"tool_calls": [
            {"index": 1, "id": "b", "function": {"name": "y", "arguments": '{"q":"'}}]}}]})
        acc.feed({"choices": [{"delta": {"tool_calls": [
            {"index": 0, "function": {"arguments": 'one"}'}}]}}]})
        acc.feed({"choices": [{"delta": {"tool_calls": [
            {"index": 1, "function": {"arguments": 'two"}'}}]}}]})
        calls = acc.finish().tool_calls
        assert calls[0].arguments == {"p": "one"}
        assert calls[1].arguments == {"q": "two"}

    def test_usage_in_a_choiceless_final_chunk_is_still_read(self):
        # This chunk has no choices at all; reading it after a short-circuit
        # on empty choices is how every turn ends up looking free.
        acc = oc.Accumulator()
        acc.feed(text_chunk("hi"))
        acc.feed({"choices": [], "usage": {"prompt_tokens": 10,
                                           "completion_tokens": 4}})
        result = acc.finish()
        assert (result.input_tokens, result.output_tokens) == (10, 4)

    def test_reported_cost_is_carried_and_absence_is_none(self):
        acc = oc.Accumulator()
        acc.feed({"choices": [], "usage": {"cost": 0.0031}})
        assert acc.finish().cost_usd == 0.0031

        bare = oc.Accumulator()
        bare.feed({"choices": [], "usage": {"prompt_tokens": 1}})
        assert bare.finish().cost_usd is None      # unpriced, not free

    def test_finish_reason_is_captured(self):
        acc = oc.Accumulator()
        acc.feed({"choices": [{"delta": {}, "finish_reason": "tool_calls"}]})
        assert acc.finish().finish_reason == "tool_calls"

    def test_malformed_tool_arguments_degrade_instead_of_raising(self):
        # The model should get a tool result saying so and a chance to retry.
        acc = oc.Accumulator()
        acc.feed({"choices": [{"delta": {"tool_calls": [
            {"index": 0, "id": "a",
             "function": {"name": "x", "arguments": "{not json"}}]}}]})
        call = acc.finish().tool_calls[0]
        assert call.arguments == {}
        assert call.arguments_valid is False

    def test_empty_arguments_count_as_valid(self):
        acc = oc.Accumulator()
        acc.feed({"choices": [{"delta": {"tool_calls": [
            {"index": 0, "id": "a", "function": {"name": "x", "arguments": ""}}]}}]})
        assert acc.finish().tool_calls[0].arguments_valid is True


class TestClient:
    def test_reports_whether_a_key_is_present(self, monkeypatch):
        client = oc.Client(api_key_env="TEST_KEY_XYZ")
        monkeypatch.delenv("TEST_KEY_XYZ", raising=False)
        assert client.has_key is False
        monkeypatch.setenv("TEST_KEY_XYZ", "sk-test")
        assert client.has_key is True

    def test_a_missing_key_says_which_variable(self, monkeypatch):
        monkeypatch.delenv("TEST_KEY_XYZ", raising=False)
        client = oc.Client(api_key_env="TEST_KEY_XYZ")
        with pytest.raises(oc.ApiError) as exc:
            client.stream([], model="m")
        assert "TEST_KEY_XYZ" in str(exc.value)
        assert exc.value.kind == "no_key"

    def test_streams_text_through_the_callback(self, monkeypatch):
        monkeypatch.setenv("TEST_KEY_XYZ", "sk-test")
        seen = []

        def opener(request, timeout=None):
            body = json.loads(request.data)
            assert body["stream"] is True
            assert body["stream_options"]["include_usage"] is True
            return sse(text_chunk("Hel"), text_chunk("lo"),
                       {"choices": [], "usage": {"prompt_tokens": 5,
                                                 "completion_tokens": 2}})

        result = oc.Client(api_key_env="TEST_KEY_XYZ").stream(
            [{"role": "user", "content": "hi"}], model="test/model",
            on_text=seen.append, opener=opener)

        assert seen == ["Hel", "lo"]
        assert result.content == "Hello"
        assert (result.input_tokens, result.output_tokens) == (5, 2)

    def test_tools_are_sent_when_given(self, monkeypatch):
        monkeypatch.setenv("TEST_KEY_XYZ", "sk-test")
        captured = {}

        def opener(request, timeout=None):
            captured.update(json.loads(request.data))
            return sse(text_chunk("ok"))

        tools = [{"type": "function", "function": {"name": "t", "parameters": {}}}]
        oc.Client(api_key_env="TEST_KEY_XYZ").stream(
            [], model="m", tools=tools, opener=opener)
        assert captured["tools"] == tools
        assert captured["tool_choice"] == "auto"

    def test_the_key_is_sent_but_never_stored_on_the_client(self, monkeypatch):
        monkeypatch.setenv("TEST_KEY_XYZ", "sk-secret")
        captured = {}

        def opener(request, timeout=None):
            captured["auth"] = request.headers.get("Authorization")
            return sse(text_chunk("ok"))

        client = oc.Client(api_key_env="TEST_KEY_XYZ")
        client.stream([], model="m", opener=opener)
        assert captured["auth"] == "Bearer sk-secret"
        assert "sk-secret" not in repr(client.__dict__)

    @pytest.mark.parametrize("code,kind,phrase", [
        (401, "auth", "Authentication failed"),
        (402, "credit", "insufficient credit"),
        (429, "rate_limit", "Rate limited"),
        (500, "http", "HTTP 500"),
    ])
    def test_http_errors_are_distinguishable_and_readable(self, monkeypatch, code,
                                                          kind, phrase):
        monkeypatch.setenv("TEST_KEY_XYZ", "sk-test")
        body = json.dumps({"error": {"message": "provider says no"}}).encode()

        def opener(request, timeout=None):
            raise urllib.error.HTTPError(request.full_url, code, "err", {},
                                         io.BytesIO(body))

        with pytest.raises(oc.ApiError) as exc:
            oc.Client(api_key_env="TEST_KEY_XYZ").stream([], model="m", opener=opener)
        assert exc.value.kind == kind
        assert phrase in str(exc.value)
        assert "provider says no" in str(exc.value)   # the useful half

    def test_an_unreachable_host_is_named(self, monkeypatch):
        monkeypatch.setenv("TEST_KEY_XYZ", "sk-test")

        def opener(request, timeout=None):
            raise urllib.error.URLError("no route to host")

        with pytest.raises(oc.ApiError) as exc:
            oc.Client(api_key_env="TEST_KEY_XYZ",
                      base_url="https://example.invalid/v1").stream(
                          [], model="m", opener=opener)
        assert exc.value.kind == "unreachable"
        assert "example.invalid" in str(exc.value)

    def test_an_error_after_a_200_is_still_an_error(self, monkeypatch):
        # Providers can start streaming and then report a failure mid-stream.
        monkeypatch.setenv("TEST_KEY_XYZ", "sk-test")

        def opener(request, timeout=None):
            return sse(text_chunk("partial"),
                       {"error": {"message": "upstream exploded", "code": 502}})

        with pytest.raises(oc.ApiError) as exc:
            oc.Client(api_key_env="TEST_KEY_XYZ").stream([], model="m", opener=opener)
        assert "upstream exploded" in str(exc.value)
