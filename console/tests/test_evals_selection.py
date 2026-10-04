"""Selectors, --changed mapping, and coverage. Git is injectable except one real repo."""

import os
import shutil
import subprocess

import pytest

from evals.scenario import changed_paths, coverage, load_dir, map_changed, select

from evals_support import SAMPLE, plant_sample, write_scenario


def _two(root):
    plant_sample(root)
    body = SAMPLE.replace('id = "sample"', 'id = "builder-one"').replace(
        'subjects = ["core"]', 'subjects = ["agent:builder"]')
    # fail_checks and checks stay. Filename must match id.
    scenarios = os.path.join(root, "console", "evals", "scenarios")
    write_scenario(scenarios, "builder-one", body)
    fixtures = os.path.join(root, "console", "evals", "fixtures")
    for which in ("pass", "fail"):
        src = os.path.join(fixtures, "sample.%s.jsonl" % which)
        dst = os.path.join(fixtures, "builder-one.%s.jsonl" % which)
        shutil.copyfile(src, dst)
    skill = SAMPLE.replace('id = "sample"', 'id = "skill-one"').replace(
        'subjects = ["core"]', 'subjects = ["skill:trace-context"]')
    write_scenario(scenarios, "skill-one", skill)
    for which in ("pass", "fail"):
        shutil.copyfile(os.path.join(fixtures, "sample.%s.jsonl" % which),
                        os.path.join(fixtures, "skill-one.%s.jsonl" % which))
    return load_dir(scenarios)


def test_touching_builder_md_selects_exactly_agent_builder_scenarios(tmp_path):
    scenarios = _two(str(tmp_path))
    subjects, every, gated = map_changed([".claude/agents/builder.md"])
    chosen, meta = select(scenarios, changed={"paths": gated, "subjects": subjects, "every": every})
    assert meta["exit"] == 0
    assert [s.id for s in chosen] == ["builder-one"]


def test_skill_subdir_file_selects_skill_scenarios(tmp_path):
    scenarios = _two(str(tmp_path))
    subjects, every, _gated = map_changed([".claude/skills/trace-context/SKILL.md"])
    chosen, _meta = select(scenarios, changed={"paths": ["x"], "subjects": subjects, "every": every})
    assert [s.id for s in chosen] == ["skill-one"]


def test_core_files_select_core_scenarios(tmp_path):
    scenarios = _two(str(tmp_path))
    for path in ("CLAUDE.md", ".claude/settings.json", ".claude/skills/harness-standards/core.md"):
        subjects, every, _gated = map_changed([path])
        chosen, _meta = select(scenarios, changed={"paths": [path], "subjects": subjects, "every": every})
        assert [s.id for s in chosen] == ["sample"], path


def test_evals_dir_change_selects_every_scenario(tmp_path):
    scenarios = _two(str(tmp_path))
    subjects, every, _gated = map_changed(["console/evals/grade.py"])
    chosen, _meta = select(scenarios, changed={"paths": ["x"], "subjects": subjects, "every": every})
    assert every is True
    assert {s.id for s in chosen} == {"sample", "builder-one", "skill-one"}


def test_selector_matching_zero_scenarios_is_refusal(tmp_path):
    scenarios = _two(str(tmp_path))
    chosen, meta = select(scenarios, agent="deployer")
    assert chosen == [] and meta["exit"] == 2


def test_changed_with_no_gated_file_is_nothing_to_gate(tmp_path):
    from evals.runner import replay
    root = str(tmp_path)
    _two(root)

    def git(argv):
        if argv[0] == "diff":
            return "README.md\n"
        return " M README.md\n"

    record = replay(root, persist=False, changed=True, git=git)
    assert record["exit"] == 0
    assert record["message"] == "nothing to gate"


def test_changed_files_with_no_covering_scenario_named_uncovered_and_exit_2_only_when_zero_selected(tmp_path):
    from evals.runner import replay
    root = str(tmp_path)
    _two(root)

    def only_skill(argv):
        if argv[0] == "diff":
            return ".claude/skills/do/SKILL.md\n"
        return ""

    record = replay(root, persist=False, changed=True, git=only_skill)
    assert record["exit"] == 2
    assert "do" in record["message"] or "skill:do" in record["message"]

    agent = os.path.join(root, ".claude", "agents")
    os.makedirs(agent, exist_ok=True)
    open(os.path.join(agent, "builder.md"), "w", encoding="utf-8").write("builder\n")

    def both(argv):
        if argv[0] == "diff":
            return ".claude/agents/builder.md\n.claude/skills/do/SKILL.md\n"
        return ""

    covered = replay(root, persist=False, changed=True, git=both)
    assert covered["exit"] == 0
    assert [row["scenario"] for row in covered["scenarios"]] == ["builder-one"]
    assert "skill:do" in covered.get("uncovered", [])


def test_staged_unstaged_and_untracked_all_count(tmp_path):
    seen = {}

    def git(argv):
        seen[" ".join(argv)] = True
        if argv[:2] == ["diff", "--name-only"]:
            return "staged.md\n"
        return " M unstaged.md\n?? untracked.md\n"

    paths = changed_paths(str(tmp_path), git=git)
    assert "staged.md" in paths and "unstaged.md" in paths and "untracked.md" in paths
    assert any("status" in k and "--untracked-files=all" in k for k in seen)


def test_porcelain_rename_takes_new_path(tmp_path):
    def git(argv):
        if argv[0] == "diff":
            return ""
        return "R  old.md -> .claude/agents/builder.md\n"

    paths = changed_paths(str(tmp_path), git=git)
    assert paths == [".claude/agents/builder.md"]


def test_unresolvable_base_surfaces_git_error(tmp_path):
    def git(argv):
        raise RuntimeError("fatal: bad revision 'nope'")

    with pytest.raises(RuntimeError) as ei:
        changed_paths(str(tmp_path), base="nope", git=git)
    assert "bad revision" in str(ei.value)


def test_coverage_counts_agents_and_lists_skills_without_scenario(tmp_path):
    root = tmp_path
    agents = root / ".claude" / "agents"
    agents.mkdir(parents=True)
    (agents / "builder.md").write_text("b", encoding="utf-8")
    (agents / "analyst.md").write_text("a", encoding="utf-8")
    skills = root / ".claude" / "skills"
    (skills / "trace-context").mkdir(parents=True)
    (skills / "trace-context" / "SKILL.md").write_text("s", encoding="utf-8")
    (skills / "do").mkdir()
    (skills / "do" / "SKILL.md").write_text("s", encoding="utf-8")
    (skills / "not-a-skill").mkdir()
    (skills / "not-a-skill" / "README.md").write_text("no", encoding="utf-8")
    scenarios = _two(str(root))
    cov = coverage(str(root), scenarios)
    assert cov["agents_covered"] == ["builder"]
    assert "analyst" in cov["agents"] and "analyst" not in cov["agents_covered"]
    assert "do" in cov["uncovered"]
    assert "trace-context" in cov["skills_covered"]
    assert "not-a-skill" not in cov["skills"]


@pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")
def test_real_git_repo_in_tmp_path(tmp_path):
    subprocess.run(["git", "init"], cwd=str(tmp_path), check=True, capture_output=True)
    subprocess.run(["git", "commit", "--allow-empty", "-m", "init"],
                   cwd=str(tmp_path), check=True, capture_output=True,
                   env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
                        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"})
    target = tmp_path / ".claude" / "agents"
    target.mkdir(parents=True)
    (target / "builder.md").write_text("x", encoding="utf-8")
    paths = changed_paths(str(tmp_path))
    assert any(p.replace("\\", "/").endswith(".claude/agents/builder.md") for p in paths)
