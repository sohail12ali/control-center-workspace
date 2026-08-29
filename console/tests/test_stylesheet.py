"""One hand-written stylesheet, no build step, no linter — so these are it.

`styles.css` is ~1800 lines of plain CSS shared by every tab. Nothing checks it:
there is no bundler to warn about a duplicated selector and no framework
scoping to keep one component's rules off another's elements. A rule written
for one panel reaches the whole document, and the failure is silent — the page
still renders, just wrongly, somewhere the author was not looking.

That is not hypothetical. `.ct-bar` was defined twice: once as the chat
composer's toolbar, and 300 lines later as a 4px progress meter with
`overflow: hidden`. The second won on cascade order, so every control in the
composer — send/queue, mic, read-aloud, announce — was clipped to a 4px sliver.
The tests below would have caught it before it shipped.
"""

import collections
import os
import re

CSS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "static", "styles.css")

#: Bare single-class selectors allowed to appear as a whole rule more than
#: once, each because the repetition is deliberate and carries a comment saying
#: why. Adding to this list should take an argument, not a keystroke.
KNOWN_REPEATS = {
    # A second rule adds `position: relative` next to the comment explaining
    # the gutter it reserves for the absolutely-positioned tracker link.
    ".card",
}


def rules():
    """Every top-level rule as (selector, line). Ignores nested @media bodies.

    Comments are replaced by their own newlines rather than removed, so the
    reported line numbers point at the real file.
    """
    with open(CSS, encoding="utf-8") as fh:
        src = fh.read()
    src = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), src,
                 flags=re.S)
    out, depth, media, buf, line = [], 0, 0, "", 1
    for ch in src:
        if ch == "\n":
            line += 1
        if ch == "{":
            sel = buf.strip()
            if sel.startswith("@"):
                media += 1
            elif depth == 0:
                out.append((sel, line))
            depth += 1
            buf = ""
        elif ch == "}":
            depth -= 1
            if media and depth < media:
                media -= 1
            buf = ""
        else:
            buf += ch
    return out


def test_no_class_is_defined_twice_at_the_top_level():
    """Two rules for `.foo` means the later one silently wins.

    Restricted to selectors that are exactly one bare class, because those are
    the ones that claim a component name outright. `.foo:hover`, `.foo .bar`
    and `.foo.on` are refinements and repeat legitimately.
    """
    seen = collections.defaultdict(list)
    for sel, line in rules():
        for part in sel.split(","):
            part = part.strip()
            if re.fullmatch(r"\.[A-Za-z][\w-]*", part):
                seen[part].append(line)

    dupes = {k: v for k, v in seen.items()
             if len(v) > 1 and k not in KNOWN_REPEATS}
    assert not dupes, (
        "these classes are each defined more than once, so the later rule wins "
        "wherever they disagree — rename one, or merge them: "
        + "; ".join("%s at lines %s" % (k, v) for k, v in sorted(dupes.items())))


def test_the_hidden_attribute_is_honoured():
    """`el.hidden = true` must actually hide, whatever the element's display.

    Author styles beat the browser's stylesheet regardless of specificity, so
    with no `[hidden]` rule of our own, any component setting its own `display`
    silently stopped being hideable — the attribute was set and nothing acted
    on it. `.fpick-panel` (display: flex) hit exactly that and never closed.

    Only components that set `display` are affected, which is why this went
    unnoticed: `.cpick` sets none and had always worked.
    """
    with open(CSS, encoding="utf-8") as fh:
        css = fh.read()
    rule = re.search(r"\[hidden\]\s*\{([^}]*)\}", css)
    assert rule, "styles.css must declare a [hidden] rule of its own"
    body = rule.group(1)
    assert "display" in body and "none" in body, body
    # Without !important a later, more specific component rule wins again and
    # the bug comes back for that one component only — the hardest kind to spot.
    assert "!important" in body, "[hidden] must win over a component's display"


def test_every_class_the_js_styles_actually_exists():
    """A class name in JS with no rule behind it is a style that never applied.

    The other half of the same problem: renaming a rule and missing a caller
    fails exactly as silently as defining one twice. Only checks names that
    look like this file's own vocabulary, so utility and state classes set
    elsewhere do not produce noise.
    """
    with open(CSS, encoding="utf-8") as fh:
        css = fh.read()
    static = os.path.dirname(CSS)
    missing = []
    for name in sorted(os.listdir(static)):
        if not name.endswith(".js"):
            continue
        with open(os.path.join(static, name), encoding="utf-8") as fh:
            body = fh.read()
        # `class: "ct-gauge warn"` — the literal form this codebase writes.
        for match in re.findall(r'class:\s*"([a-z][\w\s-]*)"', body):
            for cls in match.split():
                # Prefixed names are components defined in this file; bare ones
                # (row, chip, grow) are shared utilities checked by use.
                if "-" in cls and ("." + cls) not in css:
                    missing.append("%s: .%s" % (name, cls))
    assert not missing, (
        "these classes are applied by JS but have no rule in styles.css: "
        + ", ".join(sorted(set(missing))))
