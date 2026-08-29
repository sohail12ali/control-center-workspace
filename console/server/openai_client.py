"""Streaming chat completions against an OpenAI-compatible API.

Written for OpenRouter, but it names no provider: any base URL speaking the
OpenAI chat-completions shape works, which is most of them. Stdlib `urllib`
only — the console has no runtime dependencies and this does not add one.

## Why the parsing is separated from the HTTP

`parse_sse` and `Accumulator` are pure functions over text. Every awkward part
of this protocol — chunks split mid-JSON, tool-call arguments arriving as a
dozen fragments addressed by index, `[DONE]` with no trailing newline, usage
appearing only in a final chunk that has no choices — is tested with fixture
strings and no network at all. Only `Client.stream` touches a socket, and it is
a thin loop over those two.

That split is not tidiness. Streaming bugs of this kind produce *truncated
answers*, not crashes, so they survive casual testing and surface as "the model
seems worse on this backend".

## Tool calls arrive in pieces

The wire form is deltas addressed by index:

    {"index":0,"id":"call_1","function":{"name":"read_file","arguments":"{\\"pa"}}
    {"index":0,"function":{"arguments":"th\\":\\"a.py\\"}"}}

Name and id appear once, arguments accumulate as string fragments, and several
calls interleave by index. `Accumulator` reassembles them and parses the JSON
once, at the end, when the string is finally whole.
"""

import json
import os
import urllib.error
import urllib.request

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_TIMEOUT = 180


class ApiError(RuntimeError):
    """A request failed. Carries the provider's own message where there is one."""

    def __init__(self, message, status=None, kind="error"):
        super().__init__(message)
        self.status = status
        self.kind = kind


class ToolCall:
    __slots__ = ("index", "id", "name", "arguments_raw")

    def __init__(self, index):
        self.index = index
        self.id = ""
        self.name = ""
        self.arguments_raw = ""

    @property
    def arguments(self):
        """Parsed arguments, or {} — never an exception.

        A model that emits malformed JSON should get a tool result saying so
        and a chance to retry, which is what the caller does with an empty dict
        plus the raw text. Raising here would end the turn instead.
        """
        if not self.arguments_raw.strip():
            return {}
        try:
            parsed = json.loads(self.arguments_raw)
        except ValueError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    @property
    def arguments_valid(self):
        if not self.arguments_raw.strip():
            return True
        try:
            return isinstance(json.loads(self.arguments_raw), dict)
        except ValueError:
            return False

    def as_message_part(self):
        return {"id": self.id or ("call_%d" % self.index), "type": "function",
                "function": {"name": self.name,
                             "arguments": self.arguments_raw or "{}"}}


class Result:
    """What one streamed completion produced."""

    def __init__(self):
        self.content = ""
        self.reasoning = ""
        self.tool_calls = []
        self.finish_reason = ""
        self.usage = {}
        self.model = ""

    @property
    def input_tokens(self):
        return int(self.usage.get("prompt_tokens") or 0)

    @property
    def output_tokens(self):
        return int(self.usage.get("completion_tokens") or 0)

    @property
    def cost_usd(self):
        """Some providers report cost directly; None means "not reported",
        which telemetry renders as unpriced rather than as free."""
        cost = self.usage.get("cost")
        return float(cost) if cost not in (None, "") else None


def parse_sse(stream):
    """Yield decoded JSON objects from an SSE byte or text stream.

    Tolerates: comment lines, blank separators, `[DONE]`, and a final chunk
    with no newline. A line that is not valid JSON is skipped rather than
    ending the stream — one malformed keep-alive should not truncate a reply.
    """
    for raw in stream:
        line = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else raw
        line = line.strip()
        if not line or line.startswith(":"):
            continue
        if not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if payload == "[DONE]":
            return
        try:
            yield json.loads(payload)
        except ValueError:
            continue


class Accumulator:
    """Folds streamed chunks into a Result, yielding text as it arrives."""

    def __init__(self):
        self.result = Result()
        self._calls = {}

    def feed(self, chunk):
        """Consume one chunk. Returns the text delta it carried, or ''."""
        if chunk.get("model"):
            self.result.model = chunk["model"]
        # Usage arrives in a final chunk that often has no choices at all, so
        # it must be read before anything short-circuits on an empty list.
        if chunk.get("usage"):
            self.result.usage = chunk["usage"]

        choices = chunk.get("choices") or []
        if not choices:
            return ""
        choice = choices[0]
        if choice.get("finish_reason"):
            self.result.finish_reason = choice["finish_reason"]

        delta = choice.get("delta") or choice.get("message") or {}
        text = ""

        reasoning = delta.get("reasoning")
        if isinstance(reasoning, str) and reasoning:
            self.result.reasoning += reasoning

        content = delta.get("content")
        if isinstance(content, str) and content:
            self.result.content += content
            text = content

        for part in delta.get("tool_calls") or []:
            index = int(part.get("index") or 0)
            call = self._calls.get(index)
            if call is None:
                call = ToolCall(index)
                self._calls[index] = call
            if part.get("id"):
                call.id = part["id"]
            function = part.get("function") or {}
            if function.get("name"):
                call.name = function["name"]
            if function.get("arguments"):
                call.arguments_raw += function["arguments"]

        return text

    def finish(self):
        self.result.tool_calls = [self._calls[i] for i in sorted(self._calls)]
        return self.result


class Client:
    """One configured endpoint. Holds no key — it is read per request."""

    def __init__(self, base_url=None, api_key_env="",
                 timeout=DEFAULT_TIMEOUT, extra_headers=None):
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        # "" means this provider takes no key at all — a local server such as
        # Ollama or LM Studio. Distinct from "a key is required and missing",
        # which is what `has_key` being False on a named variable means.
        self.api_key_env = api_key_env or ""
        self.timeout = timeout
        self.extra_headers = dict(extra_headers or {})

    @property
    def keyless(self):
        return not self.api_key_env

    @property
    def has_key(self):
        if self.keyless:
            return True  # nothing to have; the endpoint is the credential
        return bool(os.environ.get(self.api_key_env, "").strip())

    def _key(self):
        key = os.environ.get(self.api_key_env, "").strip()
        if not key:
            raise ApiError(
                "%s is not set. Put it in the workspace's .env file (see "
                ".env.example) or export it in the shell that starts the "
                "console. An exported value always wins over the file."
                % self.api_key_env, kind="no_key")
        return key

    def _headers(self):
        headers = {"Content-Type": "application/json"}
        # A local server rejects or ignores an Authorization header, and
        # sending one built from an empty string would be a Bearer of nothing.
        if not self.keyless:
            headers["Authorization"] = "Bearer " + self._key()
        headers.update(self.extra_headers)
        return headers

    def stream(self, messages, *, model, tools=None, temperature=None,
               max_tokens=None, on_text=None, opener=None):
        """Run one completion. Returns a Result.

        `on_text` receives each text delta as it arrives, which is what makes
        the chat stream token by token. `opener` exists so tests can drive the
        whole path with a scripted stream and no network.
        """
        body = {"model": model, "messages": messages, "stream": True,
                # Without this most providers omit usage entirely on a
                # streamed response, and every turn would look free.
                "stream_options": {"include_usage": True}}
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"
        if temperature is not None:
            body["temperature"] = temperature
        if max_tokens:
            body["max_tokens"] = max_tokens

        request = urllib.request.Request(
            self.base_url + "/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers=self._headers(), method="POST")

        accumulator = Accumulator()
        try:
            response = (opener or urllib.request.urlopen)(request,
                                                          timeout=self.timeout)
        except urllib.error.HTTPError as exc:
            raise self._http_error(exc) from None
        except urllib.error.URLError as exc:
            raise ApiError("could not reach %s (%s)" % (self.base_url, exc.reason),
                           kind="unreachable") from None

        with response:
            for chunk in parse_sse(response):
                if chunk.get("error"):
                    # Providers can report an error mid-stream, after a 200.
                    error = chunk["error"]
                    raise ApiError(error.get("message") or str(error),
                                   status=error.get("code"), kind="provider")
                text = accumulator.feed(chunk)
                if text and on_text:
                    on_text(text)
        return accumulator.finish()

    @staticmethod
    def _http_error(exc):
        """Turn an HTTPError into something a person can act on.

        The provider's own message is the useful part and is almost always in
        the body, so it is read out rather than discarded in favour of a
        status line.
        """
        try:
            detail = exc.read().decode("utf-8", "replace")
        except Exception:  # noqa: BLE001
            detail = ""
        message = detail
        try:
            parsed = json.loads(detail)
            message = (parsed.get("error") or {}).get("message") or detail
        except ValueError:
            pass

        kind = {401: "auth", 403: "auth", 402: "credit",
                429: "rate_limit"}.get(exc.code, "http")
        prefix = {
            "auth": "Authentication failed — check the API key",
            "credit": "The account has insufficient credit",
            "rate_limit": "Rate limited by the provider",
        }.get(kind, "Request failed (HTTP %s)" % exc.code)
        return ApiError("%s: %s" % (prefix, message.strip() or "no detail given"),
                        status=exc.code, kind=kind)
