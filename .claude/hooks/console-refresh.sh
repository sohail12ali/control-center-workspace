#!/usr/bin/env bash
# SessionStart/Stop hook: cheap re-index of the Delivery Console.
# Best-effort only — never blocks a session. Missing console/ or no Python
# interpreter is silent (exit 0), not an error: this template is meant to
# work before console/ is even added to a given checkout.

[ -f "console/kanban.py" ] || exit 0

for PY in python python3 "py -3"; do
  if command -v ${PY%% *} >/dev/null 2>&1; then
    $PY console/kanban.py refresh --quiet 2>/dev/null || true
    exit 0
  fi
done

exit 0
