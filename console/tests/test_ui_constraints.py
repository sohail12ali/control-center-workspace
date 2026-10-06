"""T-036 AC-61 / NFR-1: the console UI stays dependency-free vanilla ES5.

The static files are served as written. There is no bundler, no transpiler and
no package manager, so a `=>` or a statement-leading `let`/`const` is not a style
slip, it is a syntax the console promised its oldest embedded webview it would
not use. These tests state the promise once, for every `console/static/*.js`,
rather than relying on each task remembering it.

Comments are stripped before scanning so prose such as "let the page ..." at the
start of a comment line cannot trip the check. The stripping is deliberately
crude (it can only remove more text, never less syntax than a real violation
needs), which is the safe direction for a "must not appear" test.
"""

import glob
import os
import re
import shutil
import subprocess

import pytest

from server.paths import find_repo_root

ROOT = find_repo_root()
STATIC = os.path.join(ROOT, "console", "static")


def _static_js():
    return sorted(glob.glob(os.path.join(STATIC, "*.js")))


def _code(path):
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    text = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)
    return re.sub(r"(?m)(^|\s)//.*$", r"\1", text)


def test_there_are_scripts_to_check():
    names = [os.path.basename(p) for p in _static_js()]
    assert "core.js" in names and "app.js" in names


def test_ac61_no_arrow_functions_in_any_static_script():
    hits = []
    for path in _static_js():
        for n, line in enumerate(_code(path).splitlines(), 1):
            if "=>" in line:
                hits.append("%s:%d: %s" % (os.path.basename(path), n, line.strip()[:80]))
    assert not hits, "arrow function in console/static: %s" % hits


def test_ac61_no_statement_leading_let_or_const_in_any_static_script():
    leading = re.compile(r"(^|[;{}])\s*(let|const)\s+[A-Za-z_$\[{]")
    hits = []
    for path in _static_js():
        for n, line in enumerate(_code(path).splitlines(), 1):
            if leading.search(line):
                hits.append("%s:%d: %s" % (os.path.basename(path), n, line.strip()[:80]))
    assert not hits, "let/const declaration in console/static: %s" % hits


def test_ac61_the_scanner_catches_what_it_claims_to():
    # A scanner that finds nothing proves nothing until it is shown to find
    # something. Fixtures here are strings, never written into console/static.
    leading = re.compile(r"(^|[;{}])\s*(let|const)\s+[A-Za-z_$\[{]")
    assert leading.search("  const x = 1;")
    assert leading.search("a(); let y = 2;")
    assert leading.search("if (a) { const z = 3; }")
    assert not leading.search("var constant = 1;")
    assert not leading.search("var s = 'let me';")


def test_ac61_no_package_manifest_appears():
    # The console has no build step; a package.json would be the first sign of one.
    for rel in ("package.json", os.path.join("console", "package.json"),
                os.path.join("console", "static", "package.json")):
        assert not os.path.exists(os.path.join(ROOT, rel)), "%s exists" % rel


def test_ac61_dev_requirements_are_unchanged_against_head():
    git = shutil.which("git")
    if not git:
        pytest.skip("git not available")
    probe = subprocess.run([git, "-C", ROOT, "rev-parse", "--verify", "HEAD"],
                           capture_output=True, text=True)
    if probe.returncode != 0:
        pytest.skip("not a git checkout with a HEAD")
    diff = subprocess.run([git, "-C", ROOT, "diff", "HEAD", "--", "console/requirements-dev.txt"],
                          capture_output=True, text=True)
    assert diff.returncode == 0
    assert diff.stdout == "", "console/requirements-dev.txt changed:\n" + diff.stdout
