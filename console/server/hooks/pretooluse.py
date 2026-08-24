"""PreToolUse hook: ask the Delivery Console before a gated tool runs.

The Claude CLI spawns this script with the tool call on stdin and obeys the
JSON verdict on stdout. It POSTs the call to the console, which parks the
request until a human answers in the chat UI (or the timeout hits), then
prints the CLI's expected shape and exits 0.

Standalone by design — stdlib only, no package imports — because the CLI runs
it from an arbitrary cwd with whatever interpreter the settings file named.
Every failure is fail-closed: bad arguments, unreadable stdin, or an
unreachable console all deny the tool with a reason the agent can read.
"""

import argparse
import json
import sys
import urllib.request

# Longer than the server's own approval timeout, so the deny-with-reason from
# a server-side timeout wins over a blunt client-side one.
HTTP_TIMEOUT = 340


def verdict(decision, reason):
    """Print the CLI's expected shape and leave. Always exit 0 — a non-zero
    exit would surface as a hook error rather than a decision."""
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        },
    }))
    sys.exit(0)


def main():
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--chat", default="")
    ap.add_argument("--port", type=int, default=0)
    try:
        args, _ = ap.parse_known_args()
    except SystemExit:
        verdict("deny", "console approval hook got bad arguments")
        return
    if not args.chat or not args.port:
        verdict("deny", "console approval hook is missing --chat/--port")
        return

    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        verdict("deny", "console approval hook could not read the tool call")
        return

    body = json.dumps({
        "chat": args.chat,
        "tool_name": payload.get("tool_name") or "",
        "tool_input": payload.get("tool_input") or {},
        "tool_use_id": payload.get("tool_use_id") or "",
        "cwd": payload.get("cwd") or "",
        "permission_mode": payload.get("permission_mode") or "",
    }).encode("utf-8")

    req = urllib.request.Request(
        "http://127.0.0.1:%d/api/agents/hooks/pretooluse" % args.port,
        data=body,
        headers={"Content-Type": "application/json", "X-Console-Request": "1"},
    )
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            answer = json.load(resp)
    except Exception as e:  # noqa: BLE001 - anything here means "no human reachable"
        verdict("deny", "console unreachable (%s) — denied fail-closed"
                % e.__class__.__name__)
        return

    verdict(answer.get("decision", "deny") or "deny", answer.get("reason", ""))


if __name__ == "__main__":
    main()
