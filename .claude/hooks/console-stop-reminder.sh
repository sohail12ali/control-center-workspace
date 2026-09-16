#!/usr/bin/env bash
# Stop hook: reminds an agent to comment, move, or release a ticket it still
# holds claimed with no update recorded since the claim (T-017 FR-10).
# Best-effort only — never blocks a session end. Missing console/ or no
# Python interpreter is silent (exit 0), same contract as console-refresh.sh.

[ -f "console/kanban.py" ] || exit 0

for PY in python python3 "py -3"; do
  if command -v ${PY%% *} >/dev/null 2>&1; then
    $PY console/kanban.py stop-hook check 2>/dev/null || true
    exit 0
  fi
done

exit 0
