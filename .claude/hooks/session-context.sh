#!/usr/bin/env bash
# SessionStart hook: inject active/blocked tickets from artifact-map.md
set -e

MAP="knowledge-center/artifact-map.md"
[ -f "$MAP" ] || exit 0

# Pull Active and Blocked sections (stop at next ## heading)
CONTEXT=$(awk '
  /^## Active/        { inA=1; print; next }
  /^## Blocked/       { inA=1; print; next }
  /^## Completed/     { inA=0 }
  /^## Archived/      { inA=0 }
  inA { print }
' "$MAP")

# Skip if both sections are empty
LINES=$(printf '%s\n' "$CONTEXT" | grep -c '^- ' || true)
[ "$LINES" = "0" ] && exit 0

# JSON-escape: backslashes, quotes, newlines
ESCAPED=$(printf '%s' "$CONTEXT" | python -c 'import json,sys; print(json.dumps(sys.stdin.read()))')

printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":%s}}\n' "$ESCAPED"
