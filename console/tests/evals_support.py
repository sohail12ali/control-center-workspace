"""Builders for raw stream-json lines. Shared by the evals tests, not conftest."""

import json
import os
import subprocess
import threading


def init(model="claude-test"):
    return {"type": "system", "subtype": "init", "session_id": "s",
            "model": model, "tools": [], "cwd": ""}


def assistant_text(text):
    return {"type": "assistant", "message": {"role": "assistant", "content": [
        {"type": "text", "text": text}]}}


def assistant_tool(name, args, tid="tool-1"):
    return {"type": "assistant", "message": {"role": "assistant", "content": [
        {"type": "tool_use", "id": tid, "name": name, "input": args or {}}]}}


def result(**kw):
    raw = {"type": "result", "subtype": "success", "is_error": False,
           "result": kw.pop("result_text", ""), "duration_ms": 1, "num_turns": 1}
    if "usage" not in kw:
        raw["usage"] = {"input_tokens": 3, "output_tokens": 2}
    else:
        usage = kw.pop("usage")
        if usage is not None:
            raw["usage"] = usage
    if "total_cost_usd" not in kw:
        raw["total_cost_usd"] = 0.01
    raw.update(kw)
    return raw


def stream_tool(name, args, tid="tool-1", index=0):
    """Partial tool block: start, then stop. The complete assistant message is separate."""
    return [
        {"type": "stream_event", "event": {
            "type": "content_block_start", "index": index,
            "content_block": {"type": "tool_use", "id": tid, "name": name}}},
        {"type": "stream_event", "event": {"type": "content_block_delta", "index": index,
                                            "delta": {"type": "input_json_delta",
                                                      "partial_json": json.dumps(args or {})}}},
        {"type": "stream_event", "event": {"type": "content_block_stop", "index": index}},
    ]


def stream_text_partial():
    return [
        {"type": "stream_event", "event": {
            "type": "content_block_start", "index": 0,
            "content_block": {"type": "text", "text": ""}}},
        {"type": "stream_event", "event": {"type": "content_block_stop", "index": 0}},
    ]


def dumps(events):
    return "".join(json.dumps(ev) + "\n" for ev in events)


def write_fixture(directory, scenario_id, which, events):
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, "%s.%s.jsonl" % (scenario_id, which))
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(dumps(events))
    return path


def write_scenario(directory, scenario_id, body):
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, scenario_id + ".toml")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(body)
    return path


SAMPLE = """\
[scenario]
id = "sample"
title = "Sample"
persona = "analyst"
prompt = "Say hello."
subjects = ["core"]
mode = "plan"
max_tool_calls = 25
fail_checks = ["said-hello"]

[[source]]
file = "CLAUDE.md"
quote = "every agent turn starts with `trace-context`"

[[check]]
id = "said-hello"
kind = "text"
scope = "final"
match = "hello"
why = "the reply says hello"

[[check]]
id = "done"
kind = "end"
disposition = "completed"
"""


def plant_sample(root, quote_ok=True):
    """A tmp repo with one non-vacuous scenario and two fixtures."""
    scenarios = os.path.join(root, "console", "evals", "scenarios")
    fixtures = os.path.join(root, "console", "evals", "fixtures")
    write_scenario(scenarios, "sample", SAMPLE)
    quote = "every agent turn starts with `trace-context`" if quote_ok else "not the quote"
    claude = os.path.join(root, "CLAUDE.md")
    with open(claude, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# Notes\n\n%s\n" % quote)
    write_fixture(fixtures, "sample", "pass", [
        init(), assistant_text("hello there"), result(result_text="hello there")])
    write_fixture(fixtures, "sample", "fail", [
        init(), assistant_text("nope"), result(result_text="nope")])
    return scenarios, fixtures


class _In:
    def __init__(self):
        self.buf = []
        self.closed = False

    def write(self, text):
        self.buf.append(text)
        return len(text)

    def flush(self):
        return None

    def close(self):
        self.closed = True


class _Out:
    def __init__(self, lines, block, release):
        self._lines = list(lines)
        self._i = 0
        self._block = block
        self._release = release

    def readline(self):
        if self._block and self._i >= len(self._lines):
            self._release.wait(timeout=5)
            return ""
        if self._i >= len(self._lines):
            return ""
        line = self._lines[self._i]
        self._i += 1
        if not line.endswith("\n"):
            line += "\n"
        return line


class FakeProc:
    """Scripted child. Records stdin, terminate, and kill. Can ignore terminate."""

    def __init__(self, lines=None, block=False, ignore_terminate=False):
        self.stdin = _In()
        self._release = threading.Event()
        self.stdout = _Out(lines or [], block, self._release)
        self.returncode = None
        self.pid = 4242
        self.calls = []
        self.ignore_terminate = ignore_terminate
        self.args = None
        self.kwargs = None

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        if self.returncode is None:
            raise subprocess.TimeoutExpired("fake", timeout)
        return self.returncode

    def terminate(self):
        self.calls.append("terminate")
        if not self.ignore_terminate:
            self.returncode = 1
            self._release.set()

    def kill(self):
        self.calls.append("kill")
        self.returncode = -9
        self._release.set()
