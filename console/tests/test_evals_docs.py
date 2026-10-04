"""README and package bounds. The README quotes no prompt file."""

import ast
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVALS = os.path.join(ROOT, "evals")


def _readme():
    return open(os.path.join(EVALS, "README.md"), encoding="utf-8").read()


def test_every_check_kind_in_grade_py_appears_in_readme():
    from evals.grade import KINDS
    text = _readme()
    for kind in KINDS:
        assert kind in text


def test_readme_states_replay_does_not_prove_live_behaviour_and_one_live_pass_is_not_reliability():
    text = _readme().lower()
    assert "not prove live" in text or "does not prove live" in text
    assert "one live pass is not reliability" in text


def test_readme_mentions_grader_version_and_deferred_claim_scenarios():
    text = _readme()
    assert "GRADER_VERSION" in text
    assert "Claim before work" in text
    assert "stop on a claim conflict" in text


def test_evals_package_never_references_env_files_or_dotenv():
    for name in os.listdir(EVALS):
        if not name.endswith(".py"):
            continue
        text = open(os.path.join(EVALS, name), encoding="utf-8").read()
        assert "dotenv" not in text
        assert ".env" not in text.replace("os.environ", "")
        if name != "runner.py":
            assert "os.environ" not in text
    runner = open(os.path.join(EVALS, "runner.py"), encoding="utf-8").read()
    assert runner.count("os.environ") == 1


def test_evals_package_is_exactly_three_modules_and_stdlib_only():
    names = {n for n in os.listdir(EVALS) if n.endswith(".py")}
    assert names == {"__init__.py", "scenario.py", "grade.py", "runner.py"}
    allowed = set(sys.stdlib_module_names) | {"server", "evals"}
    for name in names:
        tree = ast.parse(open(os.path.join(EVALS, name), encoding="utf-8").read())
        for node in ast.walk(tree):
            modules = []
            if isinstance(node, ast.Import):
                modules = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules = [node.module]
            for mod in modules:
                assert mod.split(".")[0] in allowed, mod
