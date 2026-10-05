"""Read-only close-check and liveness sweep for T-021.

Imports evaluate/scan only. Never calls ticket_gate or a mutating verb.
Hashes every file under knowledge-center/artifacts before and after and exits
non-zero if any byte changed.
"""

import hashlib
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, os.path.join(ROOT, "console"))

from server import close_check, ticket_liveness, tickets  # noqa: E402


def snapshot(base):
    out = {}
    for dirpath, _, files in os.walk(base):
        for name in files:
            path = os.path.join(dirpath, name)
            digest = hashlib.sha256()
            with open(path, "rb") as fh:
                digest.update(fh.read())
            out[path] = digest.hexdigest()
    return out


def main():
    artifacts = os.path.join(ROOT, "knowledge-center", "artifacts")
    before = snapshot(artifacts)
    rows = []
    for name in sorted(os.listdir(artifacts)):
        folder = os.path.join(artifacts, name)
        if not os.path.isfile(os.path.join(folder, "ticket.toml")):
            continue
        ticket = tickets.load(ROOT, name)
        if ticket is None:
            continue
        verdict = close_check.evaluate(ROOT, name)
        live = ticket_liveness.evaluate(ROOT, name)
        findings = live.get("findings") or []
        finding = findings[0]["code"] if findings else "-"
        rows.append((ticket, verdict, finding))
    after = snapshot(artifacts)
    changed = [p for p in set(before) | set(after) if before.get(p) != after.get(p)]

    print("id\tlane\tclose\tblocks\twarnings\tliveness")
    done_pass = done_empty = done_phantom = done_prose = 0
    done_n = 0
    for ticket, verdict, finding in rows:
        blocks = ",".join(b.get("code", "") for b in verdict.get("blocks") or []) or "-"
        warns = ",".join(w.get("code", "") for w in verdict.get("warnings") or []) or "-"
        close = "ok" if verdict.get("ok") else "block"
        print("%s\t%s\t%s\t%s\t%s\t%s" % (
            ticket.get("id"), ticket.get("stage"), close, blocks, warns, finding or "-"))
        if ticket.get("stage") == "done":
            done_n += 1
            ev = verdict.get("evidence") or {}
            done_pass += ev.get("pass_rows") or 0
            done_empty += ev.get("empty") or 0
            done_phantom += ev.get("phantom") or 0
            done_prose += ev.get("prose_only") or 0
    prose_share = (100.0 * done_prose / done_pass) if done_pass else 0.0
    print("calibration done_tickets=%d pass_rows=%d evidence_empty=%d evidence_phantom=%d prose_only=%d prose_share=%.1f%%" % (
        done_n, done_pass, done_empty, done_phantom, done_prose, prose_share))
    print("files changed: %d" % len(changed))
    if changed:
        for path in sorted(changed)[:20]:
            print("CHANGED", path)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
