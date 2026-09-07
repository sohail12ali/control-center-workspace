"""Windows no-window spawn hygiene, applied at every Python process-spawn
site that could otherwise flash a console window under a windowless GUI
parent (the desktop shell).

Defensive hygiene, not a fix — see `T-003-decision-log.md` § "Cause B scope":
Phase 0 smoke found the sites this module touches do not currently reproduce
a stray console (children already inherit the sidecar's hidden console).
This guards against a windowless-parent scenario the probe didn't hit,
without overclaiming a defect was fixed.

No-op on POSIX: every function here returns `0`/`{}` off Windows, so a caller
can always add `creationflags=no_window_flags(...)` or `**popen_kwargs()`
unconditionally.
"""

from __future__ import annotations

import os

#: Win32 CREATE_NO_WINDOW — suppresses the console window a spawned child
#: would otherwise get from a windowless (or hidden-console) parent.
CREATE_NO_WINDOW = 0x08000000


def no_window_flags(extra=0):
    """`extra` OR'd with `CREATE_NO_WINDOW` on Windows; `extra` unchanged
    elsewhere. Callers keep any flags they already pass (e.g.
    `CREATE_NEW_PROCESS_GROUP`)."""
    if os.name == "nt":
        return extra | CREATE_NO_WINDOW
    return extra


def popen_kwargs():
    """kwargs to splat into `subprocess.Popen`/`subprocess.run` — only ever
    `creationflags` on `nt`, so a caller's own stdio/cwd/etc. choices are
    untouched. `{}` on POSIX."""
    if os.name == "nt":
        return {"creationflags": CREATE_NO_WINDOW}
    return {}
