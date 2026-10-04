"""Replay (no process) and live (opt-in claude) eval entry points.

Replay proves the graders and the fixtures. It does not prove that a live
agent will behave. One live pass is not reliability.
"""

import json
import os
import queue
import subprocess
import sys
import threading
import time
import uuid

from server import procs
from server.paths import resolve_rel

from evals import scenario as scenario_mod
from evals.grade import (
    BAD_FIXTURE,
    GOLDEN_FAILED,
    GRADER_VERSION,
    MUST_FAIL_PASSED,
    GradingError,
    Problem,
    TranscriptView,
    classify,
    grade,
    parse_lines,
    primary,
)

FOOTER = "replay proves the graders and fixtures, not live agent behaviour"
RUN_FIELDS = ("run_id", "grader_version", "git_head", "backend", "selected", "complete")
SCENARIO_FIELDS = ("scenario", "scenario_sha256", "mode", "verdict", "class", "reason",
                   "checks", "usage", "model", "duration_ms", "transcript")
LIVE_BACKEND = "claude"


def _ci_refused():
    """True when env CI is set to anything other than 0 or false."""
    raw = os.environ.get("CI")
    if raw is None or str(raw).strip() == "":
        return False
    return str(raw).strip().lower() not in ("0", "false")


def _child_env(repo_root):
    """Environment handed to a live child. Same deny-list as a chat session."""
    return procs.clean_env(repo_root)


def git_head(repo_root):
    """HEAD sha from .git files only. Never spawns git. Unknown on any miss."""
    try:
        return _read_head(repo_root)
    except OSError:
        return "unknown"


def _read_head(repo_root):
    git = os.path.join(repo_root, ".git")
    if os.path.isfile(git):
        with open(git, "r", encoding="utf-8") as fh:
            text = fh.read()
        marker = "gitdir:"
        line = next((ln for ln in text.splitlines() if ln.strip().startswith(marker)), "")
        if not line:
            return "unknown"
        dest = line.split(":", 1)[1].strip()
        git = dest if os.path.isabs(dest) else os.path.normpath(os.path.join(repo_root, dest))
    if not os.path.isdir(git):
        return "unknown"
    with open(os.path.join(git, "HEAD"), "r", encoding="utf-8") as fh:
        head = fh.read().strip()
    if head.startswith("ref:"):
        ref = head.split(":", 1)[1].strip()
        loose = os.path.join(git, *ref.split("/"))
        if os.path.isfile(loose):
            with open(loose, "r", encoding="utf-8") as fh:
                sha = fh.read().strip()
            return sha or "unknown"
        packed = os.path.join(git, "packed-refs")
        if os.path.isfile(packed):
            with open(packed, "r", encoding="utf-8") as fh:
                for raw in fh:
                    if not raw.strip() or raw.startswith("#") or raw.startswith("^"):
                        continue
                    parts = raw.split()
                    if len(parts) >= 2 and parts[1] == ref:
                        return parts[0]
        return "unknown"
    if head and all(c in "0123456789abcdefABCDEF" for c in head) and len(head) >= 7:
        return head
    return "unknown"


def usage_of(raw_result, repo_root):
    """Tokens and cost from the raw result only. Missing is null, never zero."""
    raw = raw_result if isinstance(raw_result, dict) else {}
    usage = raw.get("usage") if isinstance(raw.get("usage"), dict) else None
    if "usage" not in raw or usage is None:
        inp = out = None
    else:
        inp = usage["input_tokens"] if "input_tokens" in usage else None
        out = usage["output_tokens"] if "output_tokens" in usage else None
    if "total_cost_usd" in raw and isinstance(raw.get("total_cost_usd"), (int, float)) \
            and not isinstance(raw.get("total_cost_usd"), bool):
        cost, source = raw["total_cost_usd"], "backend"
    elif inp is not None and out is not None:
        from server import telemetry
        cost, source = telemetry.price(repo_root, raw.get("model") or "", inp, out)
        if cost is None:
            source = "unknown"
    else:
        cost, source = None, "unknown"
    return {"input_tokens": inp, "output_tokens": out, "cost_usd": cost,
            "cost_source": source, "render": render_usage(
                {"input_tokens": inp, "output_tokens": out, "cost_usd": cost,
                 "cost_source": source})}


def replay_usage():
    row = {"input_tokens": None, "output_tokens": None, "cost_usd": None,
           "cost_source": "n/a"}
    row["render"] = "n/a (replay)"
    return row


def render_usage(usage):
    if not usage:
        return "UNKNOWN"
    if usage.get("cost_source") == "n/a":
        return "n/a (replay)"
    if usage.get("input_tokens") is None or usage.get("output_tokens") is None \
            or usage.get("cost_usd") is None:
        return "UNKNOWN"
    return "%s/%s $%s" % (usage["input_tokens"], usage["output_tokens"], usage["cost_usd"])


def totals(rows):
    """Sum known numbers. Replay rows (n/a) are not unknown. Any null is partial."""
    unknown = 0
    tin = tout = 0
    cost = 0.0
    saw_cost = False
    for row in rows:
        usage = row.get("usage") or {}
        if usage.get("cost_source") == "n/a":
            continue
        missing = False
        if usage.get("input_tokens") is None:
            missing = True
        else:
            tin += usage["input_tokens"]
        if usage.get("output_tokens") is None:
            missing = True
        else:
            tout += usage["output_tokens"]
        if usage.get("cost_usd") is None:
            missing = True
        else:
            cost += usage["cost_usd"]
            saw_cost = True
        if missing:
            unknown += 1
    return {"input_tokens": tin, "output_tokens": tout,
            "cost_usd": cost if saw_cost or unknown == 0 else None,
            "complete": unknown == 0, "unknown_scenarios": unknown}


def _dirs(repo_root, scenarios_dir, fixtures_dir):
    base = os.path.join(repo_root, "console", "evals")
    return (scenarios_dir or os.path.join(base, "scenarios"),
            fixtures_dir or os.path.join(base, "fixtures"))


def _read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def _grade_text(text, scenario, strict):
    view = parse_lines(text, strict=strict)
    results = grade(view, scenario.checks)
    return view, results


def grade_transcript(path, scenario, strict=True):
    return _grade_text(_read(path), scenario, strict)


def _scenario_row(scenario, *, mode, verdict, cls, reason, checks, usage, model,
                  duration_ms, transcript):
    return {
        "scenario": scenario.id,
        "scenario_sha256": scenario.sha256,
        "mode": mode,
        "verdict": verdict,
        "class": cls,
        "reason": reason,
        "checks": checks,
        "usage": usage,
        "model": model,
        "duration_ms": duration_ms,
        "transcript": transcript,
    }


def _finish(problems, checks):
    top = primary(problems)
    if top is None:
        return "pass", "", ""
    return "fail", top.cls, top.reason


def _replay_one(repo_root, scenario, transcript_path):
    if transcript_path:
        try:
            view, results = grade_transcript(transcript_path, scenario, strict=True)
        except GradingError as exc:
            problems = [Problem("grading", exc.reason, exc.detail)]
            verdict, cls, reason = _finish(problems, [])
            return _scenario_row(scenario, mode="replay", verdict=verdict, cls=cls,
                                 reason=reason, checks=[], usage=replay_usage(),
                                 model="", duration_ms=0, transcript=transcript_path)
        problems = classify(view, results, {})
        verdict, cls, reason = _finish(problems, results)
        return _scenario_row(scenario, mode="replay", verdict=verdict, cls=cls,
                             reason=reason, checks=results, usage=replay_usage(),
                             model=view.model, duration_ms=0, transcript=transcript_path)

    problems = list(preflight_problems(repo_root, scenario))
    checks = []
    model = ""
    for which, expect in (("pass", "pass"), ("fail", "fail")):
        path = scenario.fixture_path(which)
        try:
            view, results = grade_transcript(path, scenario, strict=True)
        except GradingError as exc:
            problems.append(Problem("grading", BAD_FIXTURE, "%s: %s" % (which, exc.detail)))
            continue
        if which == "pass":
            checks = results
            model = view.model
            if any(not r.get("ok") for r in results):
                bad = next(r for r in results if not r.get("ok"))
                problems.append(Problem(
                    "grading", GOLDEN_FAILED, bad.get("id") or "",
                    ((bad.get("evidence") or {}).get("excerpt") or "")))
        else:
            by_id = {r.get("id"): r for r in results}
            for fid in scenario.fail_checks:
                row = by_id.get(fid)
                if row is None or row.get("ok"):
                    problems.append(Problem("grading", MUST_FAIL_PASSED, fid))
    verdict, cls, reason = _finish(problems, checks)
    return _scenario_row(scenario, mode="replay", verdict=verdict, cls=cls, reason=reason,
                         checks=checks, usage=replay_usage(), model=model, duration_ms=0,
                         transcript=scenario.fixture_path("pass"))


def preflight_problems(repo_root, scenario):
    return scenario_mod.preflight(repo_root, scenario)


def _record(repo_root, rows, *, backend, selected, run_id=None, complete=None):
    if complete is None:
        complete = True if backend == "replay" else totals(rows)["complete"]
    return {
        "run_id": run_id or uuid.uuid4().hex[:12],
        "grader_version": GRADER_VERSION,
        "git_head": git_head(repo_root),
        "backend": backend,
        "selected": selected,
        "complete": complete,
        "scenarios": rows,
        "exit": 0 if rows and all(r["verdict"] == "pass" for r in rows) else (1 if rows else 0),
    }


def write_results(cache_dir, record):
    dest = os.path.join(cache_dir, record["run_id"])
    os.makedirs(dest, exist_ok=True)
    path = os.path.join(dest, "results.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2, sort_keys=True)
        fh.write("\n")
    return path


def ascii_text(text):
    return (text or "").encode("ascii", "backslashreplace").decode("ascii")


def format_table(record, *, footer=True):
    lines = ["id  verdict  class  checks  usage"]
    for row in record.get("scenarios") or []:
        checks = row.get("checks") or []
        ok = sum(1 for c in checks if c.get("ok"))
        lines.append(ascii_text("%s  %s  %s  %d/%d  %s" % (
            row["scenario"], row["verdict"], row["class"] or "-",
            ok, len(checks), render_usage(row.get("usage")))))
        if row["verdict"] != "pass":
            failed = next((c for c in checks if not c.get("ok")), None)
            excerpt = ""
            if failed:
                excerpt = ((failed.get("evidence") or {}).get("excerpt") or "")
            lines.append(ascii_text("%s / %s / %s / %s / %s" % (
                row["scenario"], (failed or {}).get("id") or "-",
                row["class"], row["reason"], excerpt)))
    rolled = totals(record.get("scenarios") or [])
    if footer:
        lines.append(FOOTER)
    if record.get("backend") != "replay" and not rolled["complete"]:
        lines.append("partial")
    if not record.get("scenarios"):
        lines.insert(1, "0 scenarios")
    return "\n".join(lines) + "\n"


def replay(repo_root, scenarios=None, *, persist=True, cache_dir=None,
           scenarios_dir=None, fixtures_dir=None, ids=None, agent="", skill="",
           changed=False, base="HEAD", transcript="", git=None, all_=False):
    sdir, fdir = _dirs(repo_root, scenarios_dir, fixtures_dir)
    if scenarios is None:
        scenarios = scenario_mod.load_dir(sdir, fdir)
    meta = {"exit": 0, "message": "", "uncovered": []}
    if changed:
        try:
            paths = scenario_mod.changed_paths(repo_root, base or "HEAD", git=git)
        except RuntimeError as exc:
            record = _record(repo_root, [], backend="replay", selected=[])
            record["exit"] = 2
            record["message"] = str(exc)
            return record
        subjects, every, gated = scenario_mod.map_changed(paths)
        if not gated:
            record = _record(repo_root, [], backend="replay", selected=[])
            record["exit"] = 0
            record["message"] = "nothing to gate"
            record["text"] = _replay_text(record)
            return record
        chosen, meta = scenario_mod.select(
            scenarios, changed={"paths": gated, "subjects": subjects, "every": every})
    else:
        chosen, meta = scenario_mod.select(
            scenarios, ids=ids, agent=agent, skill=skill, all_=all_)
    if meta["exit"]:
        record = _record(repo_root, [], backend="replay", selected=[])
        record["exit"] = meta["exit"]
        record["message"] = meta["message"]
        record["uncovered"] = meta["uncovered"]
        return record
    if meta["message"] == "nothing to gate":
        record = _record(repo_root, [], backend="replay", selected=[])
        record["exit"] = 0
        record["message"] = meta["message"]
        return record
    one = transcript if transcript and len(chosen) == 1 else ""
    rows = [_replay_one(repo_root, s, one) for s in chosen]
    record = _record(repo_root, rows, backend="replay",
                     selected=[s.id for s in chosen])
    if meta.get("uncovered"):
        record["uncovered"] = meta["uncovered"]
    if persist:
        cache = cache_dir or resolve_rel(repo_root, os.path.join("console", ".cache", "evals"))
        write_results(cache, record)
    record["text"] = _replay_text(record)
    return record


def _replay_text(record):
    if record.get("message") == "nothing to gate":
        return "nothing to gate\n" + FOOTER + "\n"
    if record.get("exit") == 2 and not record.get("scenarios"):
        return ascii_text(record.get("message") or "refused") + "\n"
    return format_table(record, footer=True)


def format_list(scenarios, cov=None):
    if not scenarios and cov is None:
        return "0 scenarios\n"
    lines = []
    for s in scenarios:
        lines.append(ascii_text("%s  %s  %s" % (
            s.id, " ".join(s.subjects), s.mode)))
    if cov is not None:
        agents = cov["agents"]
        covered = cov["agents_covered"]
        lines.append("agents %d/%d" % (len(covered), len(agents)))
        lines.append("uncovered skills %d" % len(cov["uncovered"]))
        for name in cov["uncovered"]:
            lines.append("uncovered %s" % name)
    return ("\n".join(lines) + "\n") if lines else "0 scenarios\n"


def add_parser(sub):
    p = sub.add_parser("evals", help="prompt evals: list, replay, or opt-in live")
    cmds = p.add_subparsers(dest="evals_cmd", required=True)

    def _sel(parser, live=False):
        parser.add_argument("--scenario", action="append", default=[])
        parser.add_argument("--agent", default="")
        parser.add_argument("--skill", default="")
        parser.add_argument("--all", action="store_true")
        parser.add_argument("--json", action="store_true")
        if not live:
            parser.add_argument("--changed", action="store_true")
            parser.add_argument("--base", default="HEAD")
        else:
            parser.add_argument("--confirm", action="store_true")
            parser.add_argument("--model", default="")
            parser.add_argument("--max-budget-usd", type=float, default=0.50)

    lst = cmds.add_parser("list")
    _sel(lst)
    lst.add_argument("--coverage", action="store_true")
    lst.set_defaults(func=cmd)

    rep = cmds.add_parser("replay")
    _sel(rep)
    rep.add_argument("--transcript", default="")
    rep.set_defaults(func=cmd)

    live = cmds.add_parser("live")
    _sel(live, live=True)
    live.set_defaults(func=cmd)
    return p


def cmd(args, repo_root):
    action = getattr(args, "evals_cmd", "")
    if action == "list":
        code, text = _cmd_list(args, repo_root)
    elif action == "replay":
        code, text = _cmd_replay(args, repo_root)
    elif action == "live":
        code, text = _cmd_live(args, repo_root)
    else:
        code, text = 2, "refused: unknown evals command\n"
    sys.stdout.write(ascii_text(text))
    raise SystemExit(code)


def _cmd_list(args, repo_root):
    sdir, fdir = _dirs(repo_root, None, None)
    try:
        scenarios = scenario_mod.load_dir(sdir, fdir)
    except GradingError as exc:
        return 1, "grading %s\n" % exc
    chosen, meta = scenario_mod.select(
        scenarios, ids=getattr(args, "scenario", None), agent=getattr(args, "agent", ""),
        skill=getattr(args, "skill", ""), all_=bool(getattr(args, "all", False)))
    if meta["exit"]:
        return meta["exit"], ascii_text(meta["message"]) + "\n"
    cov = scenario_mod.coverage(repo_root, scenarios) if getattr(args, "coverage", False) else None
    if getattr(args, "json", False):
        payload = {"scenarios": [{"id": s.id, "subjects": s.subjects, "mode": s.mode}
                                 for s in chosen]}
        if cov:
            payload["coverage"] = cov
        return 0, json.dumps(payload, indent=2) + "\n"
    return 0, format_list(chosen, cov)


def _cmd_replay(args, repo_root):
    try:
        record = replay(
            repo_root, persist=True,
            ids=getattr(args, "scenario", None),
            agent=getattr(args, "agent", ""),
            skill=getattr(args, "skill", ""),
            changed=bool(getattr(args, "changed", False)),
            base=getattr(args, "base", "HEAD") or "HEAD",
            transcript=getattr(args, "transcript", "") or "",
            all_=bool(getattr(args, "all", False)))
    except GradingError as exc:
        return 1, "grading %s\n" % exc
    text = record.get("text") or _replay_text(record)
    if getattr(args, "json", False):
        text = json.dumps(record, indent=2, sort_keys=True) + "\n"
    return record["exit"], text


def live_plan(scenarios, *, model="", budget=0.50):
    ids = ", ".join(s.id for s in scenarios) or "(none)"
    return (
        "scenarios: %s\nbackend: %s\nmodel: %s\nmode: plan\n"
        "caps: 180 s / 25 calls / $%.2f\ncost: UNKNOWN until run\n"
        % (ids, LIVE_BACKEND, model or "(default)", budget))


def build_live_command(backend, scenario, *, model="", max_budget_usd=0.50, repo_root=None):
    """Argv from session_argv(mode=plan) plus the budget flag. Prompt via compose_prompt."""
    argv = list(backend.session_argv(mode="plan", model=model or "",
                                     persona=scenario.persona or ""))
    if not model:
        argv = _drop_flag(argv, "--model")
    argv.extend(["--max-budget-usd", "%g" % max_budget_usd])
    prompt = backend.compose_prompt(scenario.prompt, scenario.skill or "",
                                    scenario.persona or "", repo_root)
    return argv, prompt


def _drop_flag(argv, flag):
    out = []
    skip = False
    for i, part in enumerate(argv):
        if skip:
            skip = False
            continue
        if part == flag:
            skip = True
            continue
        out.append(part)
    return out


def refusals(repo_root, scenarios, *, confirm, ids, agent, skill, all_, model, budget):
    """A refusal string, or None when live may proceed. Exit 2 either way for the plan."""
    if _ci_refused():
        return "refused: CI is set"
    if not confirm:
        return live_plan(scenarios, model=model, budget=budget)
    if not ids and not agent and not skill and not all_:
        return "refused: pass a selector or --all"
    return None


def _end(proc, grace):
    """Close stdin, wait, then tree-kill when procs provides it, else terminate then kill."""
    stdin = getattr(proc, "stdin", None)
    if stdin is not None and not getattr(stdin, "closed", False):
        try:
            stdin.close()
        except OSError:
            pass
    try:
        proc.wait(timeout=grace)
        return
    except Exception:
        pass
    killer = getattr(procs, "kill_tree", None)
    if callable(killer):
        killer(proc, grace)
        return
    if hasattr(proc, "terminate"):
        proc.terminate()
    try:
        proc.wait(timeout=grace)
        return
    except Exception:
        pass
    if hasattr(proc, "kill"):
        proc.kill()


def _drive(proc, view, *, timeout, max_calls):
    """Read stdout until result, timeout, or the tool cap. Returns a reason or ''."""
    lines = queue.Queue()

    def _read():
        stdout = getattr(proc, "stdout", None)
        if stdout is None:
            lines.put(None)
            return
        while True:
            line = stdout.readline()
            if not line:
                lines.put(None)
                return
            lines.put(line)

    threading.Thread(target=_read, daemon=True).start()
    deadline = time.monotonic() + timeout
    raw = []
    reason = ""
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            reason = "timeout"
            break
        try:
            line = lines.get(timeout=min(0.05, remaining))
        except queue.Empty:
            continue
        if line is None:
            break
        raw.append(line)
        view.feed(line, strict=False)
        if view.turn_end is not None:
            break
        if max_calls is not None and len(view.calls) > max_calls:
            reason = "tool_cap"
            break
    return reason, "".join(raw)


def run_live(repo_root, scenarios, *, spawn=subprocess.Popen, timeout=180, stop_grace=5,
             model="", max_budget_usd=0.50, env=None, cache_dir=None, run_id=None):
    from server import agent_backends
    from server import audit

    run_id = run_id or uuid.uuid4().hex[:12]
    cache = cache_dir or resolve_rel(repo_root, os.path.join("console", ".cache", "evals"))
    dest = os.path.join(cache, run_id)
    os.makedirs(dest, exist_ok=True)
    try:
        backend = agent_backends.get(repo_root, LIVE_BACKEND)
    except Exception as exc:
        backend = None
        missing = exc
    else:
        missing = None
    rows = []
    if backend is None or getattr(backend, "transport", "") != "stream_json":
        if backend is not None and getattr(backend, "transport", "") != "stream_json":
            record = _record(repo_root, [], backend=LIVE_BACKEND, selected=[], run_id=run_id,
                             complete=False)
            record["exit"] = 2
            record["message"] = "refused: backend is not stream_json"
            return record
    for scenario in scenarios:
        limits = {}
        raw_text = ""
        view = TranscriptView()
        started = time.monotonic()
        if backend is None:
            limits = {"spawn_error": True, "spawn_detail": str(missing)}
        elif backend.transport != "stream_json":
            break
        else:
            try:
                argv, prompt = build_live_command(
                    backend, scenario, model=model, max_budget_usd=max_budget_usd,
                    repo_root=repo_root)
            except FileNotFoundError as exc:
                limits = {"spawn_error": True, "spawn_detail": str(exc)}
                argv = prompt = None
            if argv is not None:
                try:
                    proc = spawn(
                        argv,
                        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                        errors="replace", bufsize=1, env=env if env is not None else _child_env(repo_root),
                        creationflags=procs.no_window_flags(
                            getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)))
                except OSError as exc:
                    limits = {"spawn_error": True, "spawn_detail": str(exc)}
                    proc = None
                if proc is not None:
                    payload = {"type": "user", "message": {"role": "user", "content": [
                        {"type": "text", "text": prompt}]}}
                    try:
                        proc.stdin.write(json.dumps(payload) + "\n")
                        proc.stdin.flush()
                    except OSError:
                        pass
                    reason, raw_text = _drive(
                        proc, view, timeout=timeout, max_calls=scenario.max_tool_calls)
                    _end(proc, stop_grace)
                    if reason == "timeout":
                        limits["timed_out"] = True
                    elif reason == "tool_cap":
                        limits["tool_cap"] = True
                        limits["max_tool_calls"] = scenario.max_tool_calls
        transcript = os.path.join(dest, scenario.id + ".raw.jsonl")
        with open(transcript, "w", encoding="utf-8") as fh:
            fh.write(raw_text)
        try:
            results = grade(view, scenario.checks) if not limits.get("spawn_error") else []
        except GradingError as exc:
            results = []
            limits.setdefault("problems_extra", []).append(
                Problem("grading", exc.reason, exc.detail))
        extra = list(preflight_problems(repo_root, scenario))
        problems = classify(view, results, limits, problems=extra)
        if limits.get("tool_cap") and not any(p.reason == "tool_cap" for p in problems):
            problems.append(Problem("model", "tool_cap", "stopped at the call cap"))
        raw = dict(view.raw_result or {})
        if view.model and "model" not in raw:
            raw["model"] = view.model
        verdict, cls, reason = _finish(problems, results)
        rows.append(_scenario_row(
            scenario, mode="live", verdict=verdict, cls=cls, reason=reason,
            checks=results, usage=usage_of(raw, repo_root) if view.raw_result else usage_of({}, repo_root),
            model=view.model or model, duration_ms=int((time.monotonic() - started) * 1000),
            transcript=transcript))
    record = _record(repo_root, rows, backend=LIVE_BACKEND,
                     selected=[s.id for s in scenarios], run_id=run_id, complete=None)
    record["complete"] = totals(rows)["complete"]
    if any(r["verdict"] != "pass" for r in rows) or not rows:
        record["exit"] = 1 if rows else 2
    outcome = "pass" if record["exit"] == 0 else "fail"
    audit.record(repo_root, "evals.live", target=run_id, detail={
        "scenarios": [s.id for s in scenarios],
        "model": model,
        "backend": LIVE_BACKEND,
        "outcome": outcome,
        "run_id": run_id,
    })
    write_results(cache, record)
    record["text"] = format_table(record, footer=False)
    return record


def _cmd_live(args, repo_root, spawn=subprocess.Popen):
    sdir, fdir = _dirs(repo_root, None, None)
    try:
        scenarios = scenario_mod.load_dir(sdir, fdir)
    except GradingError as exc:
        return 2, "refused: %s\n" % exc
    ids = list(getattr(args, "scenario", None) or [])
    agent = getattr(args, "agent", "") or ""
    skill = getattr(args, "skill", "") or ""
    all_ = bool(getattr(args, "all", False))
    confirm = bool(getattr(args, "confirm", False))
    model = getattr(args, "model", "") or ""
    budget = getattr(args, "max_budget_usd", 0.50)
    if ids or agent or skill or all_:
        chosen, meta = scenario_mod.select(
            scenarios, ids=ids, agent=agent, skill=skill, all_=all_)
    else:
        chosen, meta = [], {"exit": 0, "message": "", "uncovered": []}
    refusal = refusals(repo_root, chosen, confirm=confirm, ids=ids, agent=agent,
                       skill=skill, all_=all_, model=model, budget=budget)
    if refusal:
        return 2, refusal if refusal.endswith("\n") else refusal + "\n"
    if meta.get("exit"):
        return 2, ascii_text(meta.get("message") or "refused") + "\n"
    from server import agent_backends
    try:
        backend = agent_backends.get(repo_root, LIVE_BACKEND)
    except Exception as exc:
        return 2, "refused: %s\n" % exc
    if getattr(backend, "transport", "") != "stream_json":
        return 2, "refused: backend is not stream_json\n"
    for scenario in chosen:
        problems = preflight_problems(repo_root, scenario)
        if problems:
            return 2, "refused: %s\n" % problems[0].detail
    record = run_live(repo_root, chosen, spawn=spawn, model=model, max_budget_usd=budget)
    if record.get("message"):
        return record["exit"], ascii_text(record["message"]) + "\n"
    text = record.get("text") or ""
    if getattr(args, "json", False):
        text = json.dumps(record, indent=2, sort_keys=True) + "\n"
    return record["exit"], text


def scan_fixture_text(text):
    """Secret-shaped strings that must not be committed as fixtures."""
    flags = []
    if "C:\\Users\\" in text or "/Users/" in text or "/home/" in text:
        flags.append("profile")
    import re
    if re.search(r"sk-\w{16}", text) or re.search(r"ghp_\w{16}", text):
        flags.append("key")
    if "OPENROUTER" in text or "Bearer " in text:
        flags.append("token")
    return flags
