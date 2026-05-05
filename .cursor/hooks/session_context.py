#!/usr/bin/env python3
"""sessionStart hook: inject Active/Blocked sections from artifact-map.md (Cursor JSON)."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    map_path = root / "knowledge-center" / "artifact-map.md"
    if not map_path.is_file():
        print(json.dumps({}))
        return

    lines = map_path.read_text(encoding="utf-8", errors="replace").splitlines()
    out: list[str] = []
    capture = False
    for line in lines:
        if line.startswith("## Active") or line.startswith("## Blocked"):
            capture = True
            out.append(line)
            continue
        if line.startswith("## Completed") or line.startswith("## Archived"):
            capture = False
            continue
        if capture:
            out.append(line)

    text = "\n".join(out).strip()
    bullet_lines = sum(1 for ln in text.splitlines() if ln.startswith("- "))
    if not text or bullet_lines == 0:
        print(json.dumps({}))
        return

    prefix = (
        "## Artifact map (session context)\n\n"
        "Excerpt from `knowledge-center/artifact-map.md` (Active / Blocked only):\n\n"
    )
    ctx = prefix + text
    print(json.dumps({"additional_context": ctx}))


if __name__ == "__main__":
    try:
        main()
    except OSError:
        print(json.dumps({}))
        sys.exit(0)
