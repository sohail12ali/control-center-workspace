"""Client for the native desktop shell's loopback bridge.

## How the console finds the shell

The shell writes `console/.cache/desktop/bridge.json` when it starts —
`{base_url, token, pid, started}` — and deletes it on the way out. Nothing
else advertises the port. So "is the shell running" is answered by reading
that file and probing `/health`, and there is exactly one honest answer when
the file is absent: it is not.

That is also why this module is useful before the shell exists: with no
pointer, every helper returns `{"ok": False, "reason": "shell not running"}`,
which is what a tool result should say rather than raising into a turn.

## The token is not authentication, and this docstring will not pretend it is

The console has no auth of its own: it binds loopback and treats "can run code
as this user" as the trust boundary. The bearer token stops a *different*
local process — a stray script, a browser page trying a rebinding trick — from
driving screen capture just by guessing a port. It does not defend against
anything already running as the user, which could read the token file anyway.

## Approvals are not decided here

Whether a clipboard read may proceed is the console's call, made in front of a
human by the "Permission needed" card, before it calls this module. This file
sends requests; it never judges them.
"""

import json
import os
import urllib.error
import urllib.request

BRIDGE_FILE_REL = os.path.join("console", ".cache", "desktop", "bridge.json")

#: A quick fact (clipboard, window list) versus a screen capture are not the
#: same kind of call, and one timeout would be wrong for whichever it was not
#: tuned for — the same reasoning `agent_backends.PROBE_TIMEOUT` already uses.
DEFAULT_TIMEOUT = 5.0
LONG_TIMEOUT = 60.0

_UNAVAILABLE_REASON = "shell not running"


def _bridge_path(repo_root):
    return os.path.join(repo_root, BRIDGE_FILE_REL)


def _read_pointer(repo_root):
    """The pointer, or None when it is absent, unreadable or malformed.

    A corrupt pointer is treated exactly like a missing one: the shell it
    described is not reachable either way, and "shell not running" is the
    truthful answer to give a model.
    """
    path = _bridge_path(repo_root)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or not data.get("base_url"):
        return None
    return data


def _request(pointer, endpoint, payload=None, timeout=DEFAULT_TIMEOUT,
             opener=None):
    """One call. Returns (ok, parsed-or-reason, transport_failed).

    `transport_failed` separates "the bridge answered and said no" from "there
    was nothing there to answer". They need different messages: the first is
    the bridge's own reason, which a model should read and act on; the second
    means the shell is gone, and saying `URLError while calling /capture`
    instead of `shell not running` sends someone debugging the wrong thing.
    """
    url = pointer["base_url"].rstrip("/") + endpoint
    headers = {"Accept": "application/json"}
    token = pointer.get("token")
    if token:
        headers["Authorization"] = "Bearer %s" % token
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        url, data=data, headers=headers,
        method="POST" if payload is not None else "GET")
    try:
        with (opener or urllib.request.urlopen)(request, timeout=timeout) as resp:
            body = resp.read()
    except urllib.error.HTTPError as exc:
        # The bridge puts its reason in the body even on a 4xx, so read it
        # rather than reporting a bare status a user cannot act on.
        try:
            detail = json.loads(exc.read().decode("utf-8", "replace"))
            return (False,
                    detail.get("message") or detail.get("error") or str(exc),
                    False)
        except Exception:  # noqa: BLE001
            return False, "HTTP %s from %s" % (exc.code, endpoint), False
    except Exception as exc:  # noqa: BLE001
        # Refused, timed out, DNS, a half-open socket - the shell is not
        # answering, whatever the exception class happens to be called.
        return False, "%s while calling %s" % (type(exc).__name__, endpoint), True
    try:
        parsed = json.loads(body.decode("utf-8", "replace"))
    except ValueError:
        return False, "the bridge returned something that is not JSON", False
    if not parsed.get("ok"):
        return (False,
                parsed.get("message") or parsed.get("error") or "the bridge refused",
                False)
    return True, parsed, False


def available(repo_root, opener=None, timeout=DEFAULT_TIMEOUT):
    """(reachable, reason). `reason` is empty when it is reachable."""
    pointer = _read_pointer(repo_root)
    if pointer is None:
        return False, _UNAVAILABLE_REASON
    ok, _detail, _transport = _request(pointer, "/health", timeout=timeout,
                                       opener=opener)
    if not ok:
        # A pointer left behind by a shell that died is the common case — a
        # force-kill runs no cleanup code, so the file outlives the process —
        # and it should read the same as no pointer at all.
        return False, _UNAVAILABLE_REASON
    return True, ""


def capabilities(repo_root, opener=None):
    """What this shell can actually do, as it reports itself.

    Used to tell a model "OCR is not available" instead of letting it call a
    tool that fails. The shell reports a capability as false when the route
    does not exist, so this is the build's real surface, not the platform's
    theoretical one.
    """
    pointer = _read_pointer(repo_root)
    if pointer is None:
        return {"ok": False, "reason": _UNAVAILABLE_REASON}
    ok, detail, _transport = _request(pointer, "/health", opener=opener)
    if not ok:
        return {"ok": False, "reason": _UNAVAILABLE_REASON}
    return {"ok": True, "caps": detail.get("caps") or {}}


def _call(repo_root, endpoint, payload=None, timeout=DEFAULT_TIMEOUT,
          opener=None):
    pointer = _read_pointer(repo_root)
    if pointer is None:
        return {"ok": False, "reason": _UNAVAILABLE_REASON}
    ok, detail, transport_failed = _request(pointer, endpoint, payload=payload,
                                            timeout=timeout, opener=opener)
    if not ok:
        # One condition, one message: a stale pointer must not produce
        # "URLError while calling /capture" here and "shell not running" from
        # `available()` a line earlier.
        return {"ok": False,
                "reason": _UNAVAILABLE_REASON if transport_failed else detail}
    return detail


def state(repo_root, opener=None):
    """What the tray is showing — the same state machine that paints the icon."""
    return _call(repo_root, "/state", opener=opener)


def list_windows(repo_root, opener=None):
    return _call(repo_root, "/windows", opener=opener)


def list_monitors(repo_root, opener=None):
    return _call(repo_root, "/monitors", opener=opener)


def capture(repo_root, target="screen", window_title="", monitor_id=None,
            region=None, max_side=None, opener=None):
    """Take a screenshot. Slow, so it gets the long timeout."""
    payload = {"target": target}
    if window_title:
        payload["window_title"] = window_title
    if monitor_id is not None:
        payload["monitor_id"] = int(monitor_id)
    if region:
        payload.update({k: int(region[k]) for k in ("x", "y", "width", "height")})
    if max_side is not None:
        payload["max_side"] = int(max_side)
    return _call(repo_root, "/capture", payload=payload, timeout=LONG_TIMEOUT,
                 opener=opener)


def speak(repo_root, text, opener=None):
    """Read `text` aloud, interrupting anything already speaking.

    Returns as soon as the utterance STARTS. Holding the call open for the
    length of a spoken paragraph would tie the console's turn to the speed of
    speech, and the tray already shows the speaking state.
    """
    return _call(repo_root, "/speak", payload={"text": text or ""},
                 opener=opener)


def stop_speaking(repo_root, opener=None):
    """Cut off a reply mid-sentence. This is what makes barge-in work."""
    return _call(repo_root, "/speak/stop", payload={}, opener=opener)


def speaking(repo_root, opener=None):
    """Is something being read aloud right now?"""
    return _call(repo_root, "/speak/state", opener=opener)


def ocr(repo_root, capture_id, opener=None):
    """Read the text in a capture the shell already took.

    Takes a capture ID rather than a path on purpose: the id is the
    confinement boundary, so a tool call cannot ask for text out of an
    arbitrary file. Slow enough to want the long timeout.
    """
    return _call(repo_root, "/ocr", payload={"capture_id": capture_id},
                 timeout=LONG_TIMEOUT, opener=opener)


def clipboard_peek(repo_root, opener=None):
    """Metadata only — how much text, and a short preview.

    This exists so the approval card for a clipboard READ can be specific
    ("1,204 characters") without performing the read it is gating.
    """
    return _call(repo_root, "/clipboard/peek", opener=opener)


def clipboard_read(repo_root, opener=None):
    """The gated half. The caller must already have an answered approval."""
    return _call(repo_root, "/clipboard/read", payload={}, opener=opener)


def clipboard_write(repo_root, text, opener=None):
    """The ungated half: replaces something the user can see and can redo."""
    return _call(repo_root, "/clipboard/write", payload={"text": text or ""},
                 opener=opener)
