"""T-037 resizable layout: the splitter primitive, checked from its source.

There is no JS runner in this repo and none is added (T-037 D-20), so every
test here reads `console/static/*` as text. That is shallow on purpose: it pins
what a regexp can pin (what is hidden by default, what is gated on the wide
query, what appears exactly once) and says nothing about behaviour, which only
a browser can show. Test names are `test_p{N}_...`, so `-k "p7_"` runs one
group; the groups grow one component at a time (see T-037-components).

Several groups are vacuous until their consumer lands (P-8 has nothing to check
until a rule uses a `--sp-*` variable). They are written now, with real
helpers, so the first consumer cannot slip past them.
"""

import os
import re

STATIC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "static")

#: The one "wide" condition (T-037 D-2): the complement of the 900px cliff.
WIDE = "(min-width: 901px)"

#: The variables the six handles write (FR-5); anything else is a typo.
SP_NAMES = {"list", "rail", "side", "viewer", "lane", "dock"}


def _read(name):
    with open(os.path.join(STATIC, name), encoding="utf-8") as fh:
        return fh.read()


def _strip_comments(src, line=False):
    """Blank comments out with spaces, keeping newlines, so offsets stay valid.

    Same length in and out: an offset found in the result is the offset in the
    file. `line=True` also blanks `// ...` for JS; a `//` right after `:` or a
    quote is left alone so a URL inside a string survives.
    """
    pat = r"/\*.*?\*/" + (r"|(?<![:\"'\\])//[^\n]*" if line else "")
    return re.sub(pat, lambda m: re.sub(r"[^\n]", " ", m.group(0)), src,
                  flags=re.S)


def _depth_at(src, idx):
    """Brace nesting depth at `idx`; 0 is top level.

    Counts instead of walking, which keeps it fast enough to ask for every rule
    in the stylesheet. Needs comments stripped first, and no unbalanced brace
    inside a string (the helper test checks the stylesheet is balanced).
    """
    return src.count("{", 0, idx) - src.count("}", 0, idx)


def _match_brace(src, i):
    """Index of the `}` that closes the `{` at `i`, or -1 when unclosed."""
    depth = 0
    for j in range(i, len(src)):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if not depth:
                return j
    return -1


def _media_blocks(src, query):
    """(start, end) offsets of the body of every `@media` whose condition holds `query`.

    Spaces are ignored on both sides, so `(min-width:901px)` and
    `(min-width: 901px)` are one query; `src[start:end]` is the body.
    """
    want = re.sub(r"\s+", "", query)
    out = []
    for m in re.finditer(r"@media([^{]*)\{", src):
        if want in re.sub(r"\s+", "", m.group(1)):
            out.append((m.end(), _match_brace(src, m.end() - 1)))
    return out


def _func_body(src, name):
    """Text between the braces of `function name(...)` or `name: function (...)`.

    None when there is no such function. Used by the JS groups (P-5, P-6, P-10)
    to look inside one function instead of grepping a whole file.
    """
    n = re.escape(name)
    m = re.search(r"function\s+%s\s*\(|\b%s\s*[:=]\s*function\s*\(" % (n, n), src)
    if not m:
        return None
    start = src.index("{", m.end())
    return src[start + 1:_match_brace(src, start)]


def _leaf_rules(src, base=0):
    """(offset, selector, body) of every rule with no nested braces.

    Includes the rules inside `@media`; pair with `_depth_at` to tell top-level
    ones from nested ones. `base` shifts offsets when `src` is a slice.
    """
    return [(base + m.start(1), m.group(1).strip(), m.group(2))
            for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", src)]


def _css():
    return _strip_comments(_read("styles.css"))


def _top_level(css):
    return [r for r in _leaf_rules(css) if _depth_at(css, r[0]) == 0]


def _parts(selector):
    return [p.strip() for p in selector.split(",")]


def test_helpers_scan_braces_and_functions():
    """The scanners the groups below lean on, tried on text with known answers."""
    src = "a { x: 1 } /* } */ @media (min-width: 901px) { b { y: 2 } }"
    out = _strip_comments(src)
    assert len(out) == len(src) and out.count("{") == out.count("}")
    assert [_depth_at(out, out.index(c)) for c in "xy"] == [1, 2]
    (start, end), = _media_blocks(out, "(min-width:901px)")
    assert out[start:end].strip() == "b { y: 2 }"
    js = "var f = function (a) { if (a) { return 1; } return 2; }; function g() { x(); }"
    assert _func_body(js, "f").strip() == "if (a) { return 1; } return 2;"
    assert _func_body(js, "g").strip() == "x();"
    assert _func_body(js, "h") is None
    cut = _strip_comments("a(); // b\nc('http://x')", line=True)
    assert "// b" not in cut and "http://x" in cut and cut.count("\n") == 1
    css = _css()
    assert css.count("{") == css.count("}"), "styles.css braces are unbalanced"


def test_p7_sp_css_present_midfile_hidden_by_default():
    """AC-1.3, 1.4, 5.1 and the print rule: the handle's CSS, where and how.

    Two ways this goes wrong without a sound: the `.sp` rule is appended to the
    end of the file (where another ticket's block lives and the cascade order
    is not ours), or it ships visible by default, so a handle shows below 901px
    where nothing may be focusable or hittable.
    """
    css = _css()
    top = _top_level(css)
    sp = [r for r in top if r[1] == ".sp"]
    assert len(sp) == 1, "`.sp` must be one bare top-level rule, found %d" % len(sp)
    off, _, body = sp[0]

    # Mid-file. Never depends on another ticket's block existing: the .ob-scrim
    # check applies only when that rule is there, the 85% bound always.
    line, total = css.count("\n", 0, off) + 1, css.count("\n") + 1
    assert line < 0.85 * total, "`.sp` (line %d of %d) sits in the last 15%%" % (line, total)
    ob = [o for o, sel, _ in top if sel == ".ob-scrim"]
    assert not ob or off < ob[0], "`.sp` must come before the .ob-* block"

    # Hidden by default, above the topbar's neighbours but under the topbar.
    assert re.search(r"\bdisplay\s*:\s*none\b", body), "`.sp` must default to display: none"
    assert re.search(r"\bz-index\s*:\s*8\b", body), "`.sp` must be z-index 8"
    topbar = [int(z) for _, sel, b in top if sel == ".topbar"
              for z in re.findall(r"z-index\s*:\s*(\d+)", b)]
    assert topbar and 8 < max(topbar), "the handle must stay under the topbar"

    # Shown only in a wide block: every other rule on `.sp` that sets a display
    # other than none has to sit inside one.
    wide = _media_blocks(css, WIDE)
    shown = False
    for roff, sel, rbody in _leaf_rules(css):
        m = re.search(r"\bdisplay\s*:\s*([\w-]+)", rbody)
        if ".sp" in _parts(sel) and m and m.group(1) != "none":
            assert any(s <= roff < e for s, e in wide), "`.sp` is shown outside the wide query"
            shown = True
    assert shown, "no wide block makes `.sp` visible"

    # Its own print block, because the wide query is true for landscape paper.
    prints = [css[s:e] for s, e in _media_blocks(css, "print")]
    for cls in (r"\.sp", r"\.sp-foldbar"):
        assert any(re.search(r"(?<![\w-])%s(?![\w-])[^{]*\{[^}]*display\s*:\s*none" % cls, p)
                   for p in prints), "no print block hides %s" % cls.replace("\\", "")

    # Every class the JS will apply exists (test_stylesheet checks the literal
    # `class:` form only; the state classes are added with classList).
    for cls in ("sp", "sp-active", "sp-collapsed", "sp-dragging", "sp-foldbar"):
        assert re.search(r"\.%s(?![\w-])" % cls, css), "no rule for .%s" % cls


def test_p8_sp_vars_only_in_wide_blocks_no_grid_transition():
    """AC-5.3 and 5.4: sizes are consumed only when wide; columns never animate.

    Vacuous until the first consumer lands. The name check pins the six
    variables so a typo (`--sp-lanes`) fails here instead of silently falling
    back to the CSS default in every browser.
    """
    css = _css()
    wide = _media_blocks(css, WIDE)
    for m in re.finditer(r"var\(\s*--sp-([\w-]*)", css):
        assert m.group(1) in SP_NAMES, "unknown variable --sp-%s" % m.group(1)
        assert any(s <= m.start() < e for s, e in wide), (
            "var(--sp-%s) at line %d is outside @media %s"
            % (m.group(1), css.count("\n", 0, m.start()) + 1, WIDE))
    for _, sel, body in _leaf_rules(css):
        for name in re.findall(r"--sp-([\w-]+)\s*:", body):
            assert name in SP_NAMES, "unknown variable --sp-%s" % name
            assert not {":root", "html"} & set(_parts(sel)), "--sp-%s is set on <html>" % name
        trans = re.findall(r"\btransition(?:-property)?\s*:\s*([^;]*)", body)
        assert not any("grid-template-columns" in t for t in trans), (
            "`%s` transitions grid-template-columns" % sel)
        assert not ("grid-template-columns" in body and any(re.search(r"\ball\b", t) for t in trans)), (
            "`%s` has `transition: all` next to grid-template-columns" % sel)


def test_p8_wide_consumer_follows_its_base_rule():
    """CR-25: a wide-block rule overrides its base only if it comes later.

    Equal specificity, so source order decides. The first wide block (~882)
    precedes `.ct-split` and `.vault`; a consumer put there would lose to the
    base rule and the stored size would silently do nothing.
    """
    css = _css()
    base = {}
    for off, sel, _ in _top_level(css):
        for part in _parts(sel):
            base.setdefault(part, off)
    for s, e in _media_blocks(css, WIDE):
        for off, sel, body in _leaf_rules(css[s:e], base=s):
            if "var(--sp-" not in body:
                continue
            for part in _parts(sel):
                # the dock's state class only exists while docked: its base is #app
                key = "#app" if part == "#app.has-dock" else part
                assert key in base, "wide rule `%s` has no top-level base rule" % part
                assert base[key] < off, (
                    "wide rule `%s` (line %d) comes before its base rule (line %d)"
                    % (part, css.count("\n", 0, off) + 1, css.count("\n", 0, base[key]) + 1))


def test_p8_min_zero_kept():
    """AC-5.4: the three containers keep `min-height: 0`.

    Without it a grid or flex child refuses to shrink below its content, and
    the pane's own scroller never engages (the note above `.appshell`). The
    dock block gets the same check when it lands (T-037-19).
    """
    css = _css()
    top = _top_level(css)
    for sel in (".appshell", ".ct-split", ".vault"):
        bodies = [b for _, s, b in top if sel in _parts(s)]
        assert bodies, "no top-level `%s` rule" % sel
        assert any(re.search(r"\bmin-height\s*:\s*0\b", b) for b in bodies), (
            "`%s` lost min-height: 0" % sel)


# ---------------------------------------------------------------------------
# splitter.js (T-037-03). Comments are blanked first, so a comment may explain
# a forbidden thing without tripping the scan; strings are not blanked.
# ---------------------------------------------------------------------------

#: Source constructs splitter.js must not contain (AC-1.5). ES5 only, no markup
#: strings, no storage of its own, no HTML5 drag-and-drop (it would fight Pointer
#: Events and cannot be captured).
_JS_FORBIDDEN = {
    "arrow function": r"=>",
    "let": r"\blet\b",
    "const": r"\bconst\b",
    "template literal": r"`",
    "innerHTML": r"\binnerHTML\b",
    "localStorage": r"\blocalStorage\b",
    "draggable": r"\bdraggable\b",
    "dragstart": r"\bdragstart\b",
}


def _js():
    return _strip_comments(_read("splitter.js"), line=True)


def _quoted(js, word):
    """True when `word` is used as a whole string, or as `.word =` / `word:` (a plain key)."""
    w = re.escape(word)
    return re.search(r"([\"'])%s\1|\.%s\s*=|(?<![\w-])%s\s*:" % (w, w, w), js) is not None


def test_p2_splitter_js_is_es5_without_forbidden_constructs():
    """AC-1.5: the file loads as a plain script in the oldest webview we ship.

    The scan is proven first on a snippet that holds every forbidden construct,
    so a pattern edited into something that matches nothing cannot pass.
    """
    bad = "var f = (a) => `x${a}`; let q; const r; n.innerHTML = 1; localStorage; d.draggable; 'dragstart';"
    for name, pat in _JS_FORBIDDEN.items():
        assert re.search(pat, bad), "the %s pattern no longer matches anything" % name
    js = _js()
    assert re.search(r"\(function\s*\(C\)\s*\{\s*[\"']use strict[\"']", js), "not a strict IIFE over C"
    assert "C.splitter" in js and "function splitter" in js, "the module is empty"
    for name, pat in _JS_FORBIDDEN.items():
        m = re.search(pat, js)
        assert not m, "splitter.js contains %s at line %d" % (name, js.count("\n", 0, m.start()) + 1)


def test_p3_handle_is_an_aria_separator_with_keys_and_reset():
    """AC-1.2 and 3.1: what a screen reader and a keyboard are promised, in source.

    Only names are checked (the behaviour needs a browser): the role, the value
    attributes, an id given to a pane that has none, the five keys and the
    double-click reset.
    """
    js = _js()
    assert _quoted(js, "separator") and re.search(r"\brole\b", js), "no role=separator"
    for attr in ("aria-orientation", "aria-valuenow", "aria-valuemin", "aria-valuemax",
                 "aria-controls", "aria-label", "aria-hidden", "tabindex"):
        assert _quoted(js, attr), "no %s" % attr
    assert re.search(r"if\s*\(\s*!\s*[\w.]+\.id\s*\)\s*[\w.]+\.id\s*=", js), (
        "aria-controls needs an id assigned to a pane that has none")
    for key in ("ArrowLeft", "ArrowRight", "Home", "End", "Enter"):
        assert _quoted(js, key), "no handling for the %s key" % key
    assert _quoted(js, "dblclick"), "no double-click reset"


def test_p4_drag_uses_capture_and_always_ends():
    """AC-2.1 and 2.2: one gesture, however it ends.

    Three things go wrong without a sound: capture is never taken (the drag dies
    over the Vault canvas), the cancel/lost-capture paths do not reach the
    function that clears the body class (the page stays unselectable), or
    something is attached to `.brandrow`, which is the desktop window-drag
    region. The class is cleared by exactly one function and all three end
    events must call it.
    """
    js = _js()
    for token in ("setPointerCapture", "requestAnimationFrame", "cancelAnimationFrame"):
        assert re.search(r"\b%s\b" % token, js), "no %s" % token
    # The resize scheduler (T-037-04) also uses a frame, so the pointer path is asked on its own.
    assert re.search(r"\brequestAnimationFrame\b", _func_body(js, "moveDrag") or ""), "moves are not frame-coalesced"
    assert re.search(r"classList\.add\(\s*[\"']sp-dragging[\"']", js), "the drag class is never set"
    enders = [n for n in re.findall(r"function\s+(\w+)\s*\(", js)
              if re.search(r"classList\.remove\(\s*[\"']sp-dragging[\"']", _func_body(js, n) or "")]
    assert len(enders) == 1, "exactly one function must clear sp-dragging, found %r" % enders
    for ev in ("pointerup", "pointercancel", "lostpointercapture"):
        m = re.search(r"addEventListener\(\s*[\"']%s[\"']\s*,\s*function\s*\([^)]*\)\s*\{" % ev, js)
        assert m, "no inline %s listener" % ev
        handler = js[m.end() - 1:_match_brace(js, m.end() - 1) + 1]
        assert re.search(r"\b%s\(" % enders[0], handler), "%s does not reach %s" % (ev, enders[0])
    assert "brandrow" not in js.lower(), "nothing may be attached to the window-drag region"
    sp = [b for _, sel, b in _top_level(_css()) if sel == ".sp"]
    assert sp and re.search(r"\btouch-action\s*:\s*none\b", sp[0]), "`.sp` needs touch-action: none"


def _fn_depth(src, idx):
    """How many function bodies enclose offset `idx` (the module's IIFE counts one).

    A brace opens a function body when `function ...)` ends right before it.
    Needs comments stripped; the module has no braces inside strings.
    """
    stack = []
    for i in range(idx):
        if src[i] == "{":
            stack.append(re.search(r"\bfunction\b[^{};]*\)\s*$", src[max(0, i - 240):i]) is not None)
        elif src[i] == "}" and stack:
            stack.pop()
    return sum(stack)


def test_p5_one_prefs_write_in_a_helper_that_reads_layout_first():
    """AC-4.1: one `prefs.set(`, in a read-modify-write helper; nothing at load.

    Two ways persistence goes wrong without a sound: a second write path (one
    per pointer-move, or one that skips the read and drops the keys another
    surface stored in the same `layout` object), and a prefs read at script
    load, when the server's prefs have not arrived yet (T-036 hydrates later).
    """
    fixture = "(function (C) { var x = C.prefs.get('a'); function f() { C.prefs.set('a', 1); } })(w)"
    assert [_fn_depth(fixture, m.start()) for m in re.finditer(r"prefs\.", fixture)] == [1, 2]
    js = _js()
    sets = [m.start() for m in re.finditer(r"\bprefs\.set\(", js)]
    assert len(sets) == 1, "exactly one prefs.set( expected, found %d" % len(sets)
    holders = [n for n in re.findall(r"function\s+(\w+)\s*\(", js)
               if "prefs.set(" in (_func_body(js, n) or "")]
    assert len(holders) == 1, "prefs.set( must sit in one named helper, found %r" % holders
    body = _func_body(js, holders[0])
    got = re.search(r"\bprefs\.get\(\s*[\"']layout[\"']", body)
    assert got and got.start() < body.index("prefs.set("), "%s must read layout before it writes" % holders[0]
    assert re.search(r"\bprefs\.set\(\s*[\"']layout[\"']", body), "the helper must write the layout key"
    for m in re.finditer(r"\bprefs\b", js):
        assert _fn_depth(js, m.start()) >= 2, "prefs used at load, line %d" % (js.count("\n", 0, m.start()) + 1)
    assert not re.search(r"\bprefs\.(del|reset)\b|\blocalStorage\b", js), "only get/set through C.prefs"


def test_p9_one_wide_constant_and_no_inline_grid_or_root_writes():
    """AC-5.2 and the JS half of 5.3.

    `901px` is counted on the raw file (comments included, as the Done Grep
    does), so the cliff cannot sneak back as a second copy or a `max-width:
    900px` constant (agents.js already carries three of those). Sizes reach the
    stylesheet only as `--sp-*` variables on the owner: never an inline grid
    column list, never anything on the root element (it would beat the
    narrow-viewport rules).
    """
    raw = _read("splitter.js")
    assert raw.count("901px") == 1, "`901px` must appear exactly once, found %d" % raw.count("901px")
    assert re.search(r"\bWIDE\s*=\s*[\"']\(min-width:\s*901px\)[\"']", raw), "WIDE must be the one wide query"
    assert not re.search(r"max-width\s*:\s*900px", raw), "no max-width: 900px constant"
    js = _js()
    for call in re.findall(r"\bmatchMedia\(([^)]*)\)", js):
        assert call.strip() == "WIDE", "matchMedia(%s): only the WIDE constant may be asked" % call
    for pat in (r"\bdocumentElement\b", r"\bgridTemplateColumns\b", r"\bgridTemplate\b",
                r"grid-template", r"[\"']:root[\"']"):
        assert not re.search(pat, js), "splitter.js touches %s" % pat
    writes = [m.group(1).strip() for m in re.finditer(r"\bsetProperty\(\s*([^,)]*)", js)]
    assert writes, "no setProperty( call: the size is never written"
    for arg in writes:
        if re.match(r"[\"']", arg):
            assert re.match(r"[\"']--sp-", arg), "setProperty(%s): only --sp-* is written" % arg
        else:
            assert re.search(r"\b%s\s*=\s*[\"']--sp-" % re.escape(arg), js), (
                "setProperty(%s): `%s` is not built from a --sp- prefix" % (arg, arg))


# ---------------------------------------------------------------------------
# splitter.js (T-037-04): the registry, the window listeners, reapplyAll and
# foldBar. Each scan is proven on small fixtures first, as P-2 and P-5 do.
# ---------------------------------------------------------------------------

_RESIZE = r"\bwindow\.addEventListener\(\s*[\"']resize[\"']"


def _handler_body(js, call):
    """Body of the function a listener call passes after `call` (a regexp match).

    The second argument is either a name (its function is looked up) or an
    inline `function (...) {`; None when it is neither.
    """
    m = re.match(r"\s*,\s*(?:function\s*\([^)]*\)\s*\{|(\w+)\s*\))", js[call.end():])
    if not m:
        return None
    if m.group(1):
        return _func_body(js, m.group(1))
    start = call.end() + m.end() - 1
    return js[start + 1:_match_brace(js, start)]


def _resize_installer(js):
    """Name of the one function that adds the window `resize` listener behind a flag.

    The test comes first in the body (`if (flag) return; flag = true;`) and the
    flag is a module-level var. None when the listener is added per attach,
    without a guard, with a flag that resets on every call, or at load.
    """
    holders = [n for n in re.findall(r"function\s+(\w+)\s*\(", js)
               if re.search(_RESIZE, _func_body(js, n) or "")]
    if len(holders) != 1:
        return None
    guard = re.match(r"\s*if\s*\(\s*(\w+)\s*\)\s*return\s*;\s*\1\s*=\s*true\s*;",
                     _func_body(js, holders[0]))
    flag = guard and re.search(r"\bvar\s+%s\b" % guard.group(1), js)
    return holders[0] if flag and _fn_depth(js, flag.start()) == 1 else None


def test_p6_listeners_once_registry_pruned_reapplyall_exposed():
    """AC-4.2 and 15.2: nothing piles up per attach, and the one reset hook exists.

    The board repaints on every search keystroke and builds a handle per lane
    each time, so a window listener added per attach, or entries that outlive
    their DOM, grow without a sound. Re-applying must also never write: a width
    saved on a big monitor has to survive one visit on a small one (D-4).
    """
    boot = 'if (on) return; on = true; window.addEventListener("resize", f);'
    fixtures = [
        ("(function (C) { var on = false; function boot() { %s } })(w)" % boot, "boot"),
        ('(function (C) { function splitter() { window.addEventListener("resize", f); } })(w)', None),
        ('(function (C) { var on; function boot() { window.addEventListener("resize", f); on = true; } })(w)', None),
        ('(function (C) { function boot() { var on = false; %s } })(w)' % boot, None),
        ('(function (C) { window.addEventListener("resize", f); })(w)', None),
    ]
    for src, want in fixtures:
        assert _resize_installer(src) == want, "the guard scan is wrong on %r" % src

    raw, js = _read("splitter.js"), _js()
    assert raw.count('addEventListener("resize"') == 1, "exactly one window resize listener expected"
    install = _resize_installer(js)
    assert install, "the resize listener must sit in one function behind `if (flag) return; flag = true;`"
    assert len(re.findall(r"\b(?:window|document)\.addEventListener\(", js)) == 1, (
        "the resize listener is the file's only window/document listener")
    assert re.search(r"\b%s\(\s*\)" % install, _func_body(js, "splitter")), "attach must call %s()" % install
    assert re.search(r"\baddEventListener\(\s*[\"']change[\"']", _func_body(js, install)), (
        "no wide-query change listener beside the resize one")

    handler = _handler_body(js, re.search(_RESIZE, js))
    assert handler and "requestAnimationFrame" in handler and re.search(r"\breapplyAll\(", handler), (
        "a resize must re-apply, coalesced into one frame")
    for what, body in (("the resize handler", handler), ("reapplyAll()", _func_body(js, "reapplyAll")),
                       ("apply()", _func_body(js, "apply"))):
        assert body is not None, "no %s" % what
        assert not re.search(r"\bwriteLayout\(|\bprefs\b", body), "%s must never write storage" % what

    funcs = re.findall(r"function\s+(\w+)\s*\(", js)
    pruners = [n for n in funcs if re.search(r"\bisConnected\b", _func_body(js, n))
               and re.search(r"\bregistry\s*=(?!=)", _func_body(js, n))]
    assert len(pruners) == 1, "exactly one function must drop disconnected entries, found %r" % pruners
    assert re.search(r"\bendDrag\(", _func_body(js, pruners[0])), (
        "a pruned entry's drag in flight must end (its body class and hook)")
    for caller in ("splitter", "reapplyAll"):
        assert re.search(r"\b%s\(" % pruners[0], _func_body(js, caller)), "%s() must prune" % caller
    body = _func_body(js, "reapplyAll")
    assert body.index(pruners[0] + "(") < body.index("apply("), "reapplyAll() must prune before it applies"
    assert re.search(r"\bC\.splitter\.reapplyAll\s*=\s*reapplyAll\b", js), "reapplyAll is not exported"
    assert not re.search(r"\bprefs\.reset\b", raw), "T-037 must not depend on C.prefs.reset (AC-15.2)"


def _fn_header_at(src, idx):
    """Header of the innermost function around `idx`, e.g. `function f(a)` or `function ()`; else None."""
    stack = []
    for i in range(idx):
        if src[i] == "{":
            m = re.search(r"\bfunction\b[^{};]*\)\s*$", src[max(0, i - 240):i])
            stack.append(m.group(0) if m else None)
        elif src[i] == "}" and stack:
            stack.pop()
    named = [h for h in stack if h]
    return named[-1] if named else None


def _queries_at_click_time(js):
    """True when `[data-panel-id]` is looked up, and only ever inside a handler.

    A handler is an anonymous function below the module's own (depth 3 or
    more: module, the function that builds the bar, the handler). A lookup in a
    named function, or at module level, runs when the bar is built or at load,
    which is the stale list the handler exists to avoid.
    """
    hits = [m.start() for m in re.finditer(r"querySelectorAll\(\s*[\"']\[data-panel-id\]", js)]
    return bool(hits) and all(re.match(r"function\s*\(", _fn_header_at(js, i) or "")
                              and _fn_depth(js, i) >= 3 for i in hits)


def test_p13_foldbar_queries_at_click_time():
    """AC-13.1: Collapse all / Expand all look the panels up when pressed.

    Overview fills its panels in as requests return and two of them remove
    themselves when empty (overview.js), so a node list taken when the bar is
    built is wrong in both directions. Settings keeps its own jump bar: foldBar
    is not wired into it.
    """
    late = ("(function (C) { function all(host, o) { return function () {"
            ' var n = host.querySelectorAll("[data-panel-id]"); }; } })(w)')
    early = ("(function (C) { function foldBar(host) {"
             ' var n = host.querySelectorAll("[data-panel-id]");'
             " return el(function () { n.forEach(f); }); } })(w)")
    assert _queries_at_click_time(late) and not _queries_at_click_time(early)
    top = '(function (C) { var n = document.querySelectorAll("[data-panel-id]"); })(w)'
    assert not _queries_at_click_time("(function (C) { function foldBar() {} })(w)")
    assert not _queries_at_click_time(top), "a lookup at load is not a lookup at click time"

    js = _js()
    assert _queries_at_click_time(js), "[data-panel-id] must be looked up inside the click handler"
    assert len(re.findall(r"\[data-panel-id\]", js)) == 1, "one lookup, no cached copy of its result"
    assert re.search(r"\bC\.splitter\.foldBar\s*=\s*foldBar\b", js), "foldBar is not exported"
    body = _func_body(js, "foldBar")
    assert body is not None, "no foldBar()"
    assert "sp-foldbar" in body and "Collapse all" in body and "Expand all" in body
    assert len(re.findall(r"\bonclick\s*:", body)) == 2, "both buttons need a click handler"
    assert re.search(r"\b_setOpen\(\s*open\s*\)", js), "panels are folded through their own _setOpen"
    assert "foldBar" not in _read("settings.js"), "Settings keeps its own jump bar"


# ---------------------------------------------------------------------------
# index.html (T-037-05): the script tag.
# ---------------------------------------------------------------------------

def _script_srcs(html):
    """`src` of every real <script> tag in document order; commented-out tags do not count."""
    html = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    return re.findall(r"<script\b[^>]*\bsrc=[\"']([^\"']+)[\"']", html)


def test_p1_script_order_core_splitter_app():
    """AC-1.1: splitter.js loads after core.js and before every consumer.

    Scripts share one global scope and run in document order: app.js, and any
    tab script that attaches a handle while it registers, must find C.splitter
    already defined, and the splitter needs C.el and C.prefs from core.js.
    desktop-chrome.js is the next script after core.js, so the tag cannot be
    tucked in behind it either. One tag, because a second would define it twice.
    """
    fixture = ('<!-- <script src="splitter.js"></script> -->'
               '<script src="a.js"></script><script defer src=\'b.js\'></script>')
    assert _script_srcs(fixture) == ["a.js", "b.js"]
    order = _script_srcs(_read("index.html"))
    for name in ("core.js", "splitter.js", "app.js", "desktop-chrome.js"):
        assert order.count(name) == 1, "%s is loaded %d times, expected once" % (name, order.count(name))
    at = order.index
    assert at("core.js") < at("splitter.js") < at("app.js"), "script order must be core.js, splitter.js, app.js"
    assert at("splitter.js") < at("desktop-chrome.js"), "splitter.js must load before desktop-chrome.js"


# ---------------------------------------------------------------------------
# The Agents surface (T-037-06..08, slice S2): agents.js and its CSS. In the
# shell the chat LIST is `.ap-rail` and the right-hand rail is `.ct-rail`.
# ---------------------------------------------------------------------------

def _agents():
    return _strip_comments(_read("agents.js"), line=True)


def _splitter_calls(js):
    """(offset, text of the option object) for every `C.splitter({...})` in `js`."""
    out = []
    for m in re.finditer(r"\bC\.splitter\(\s*\{", js):
        start = m.end() - 1
        out.append((m.start(), js[start:_match_brace(js, start) + 1]))
    return out


def _call_with(js, key):
    """The one splitter call whose `key:` is `key`, as (offset, options)."""
    pat = r"\bkey\s*:\s*[\"']%s[\"']" % re.escape(key)
    hits = [c for c in _splitter_calls(js) if re.search(pat, c[1])]
    assert len(hits) == 1, "expected one C.splitter call for %s, found %d" % (key, len(hits))
    return hits[0]


def test_agents_helpers_find_calls_and_reject_lookalikes():
    """The two scanners above, tried on text with known answers (so a typo cannot pass)."""
    js = 'x(); C.splitter({ key: "a.b", f: function () { return {}; } }); C.splitter({ key: "c.d" });'
    assert [o for o, _ in _splitter_calls(js)] == [js.index("C.splitter"), js.rindex("C.splitter")]
    assert _call_with(js, "a.b")[1].startswith("{ key") and "function" in _call_with(js, "a.b")[1]
    assert "a.b" not in _call_with(js, "c.d")[1]


def test_p12_agents_list_attach_reuses_setlistshown():
    """AC-6.1: the list divider folds through `setListShown` and adds no fold flag.

    Two things go wrong without a sound: the collapse hook flips a class or a
    new preference of its own (two states for one fold, and the reveal button
    and the handle drift apart), or the handle is left showing after the list
    is folded because setListShown never tells the splitter.
    """
    js = _agents()
    _, opts = _call_with(js, "agents.list")
    for pat in (r"\bcssVar\s*:\s*[\"']list[\"']", r"\bmin\s*:\s*180\b", r"\bmax\s*:\s*480\b",
                r"\bflexMin\s*:\s*320\b", r"\bdir\s*:\s*1\b"):
        assert re.search(pat, opts), "list splitter lacks %s" % pat
    # The naming trap: the list is `.ap-rail` here, the main pane `.ap-main`.
    pane = re.search(r"\bpane\s*:\s*([^,]+),", opts).group(1)
    flex = re.search(r"\bflexPane\s*:\s*([^,]+),", opts).group(1)
    assert ".ap-rail" in pane and ".ct-rail" not in pane, "the list pane is .ap-rail: %s" % pane
    assert ".ap-main" in flex, "the flexible pane is .ap-main: %s" % flex
    # The fold is the existing one: reads listShown, writes through setListShown.
    assert re.search(r"collapseGet\s*:\s*function\s*\(\)\s*\{\s*return\s*!\s*st\.listShown\s*;", opts)
    set_body = _func_body(opts, "collapseSet")
    assert set_body and re.search(r"\bsetListShown\(\s*!\s*off\s*\)", set_body)
    assert "collapseKey" not in opts, "the splitter must not store a second fold flag"
    assert "keepWhenCollapsed" not in opts, "a folded list hides its handle; .list-reveal restores"
    # No new fold state anywhere in agents.js.
    names = re.findall(r"prefs\.set\(\s*[\"']([\w.]+)[\"']", js)
    assert names.count("chatListHidden") == 1, "chatListHidden is written once, by setListShown"
    assert not [n for n in names if n != "chatListHidden"
                and re.search(r"hidden|fold|collapse|shown|[a-z]Off$|^off", n, re.I)], names
    flags = set(re.findall(r"\bst\.(\w*(?:Shown|Hidden|Fold\w*|Collapse\w*|Off))\b", js))
    assert flags == {"listShown"}, "a second fold flag on st: %s" % sorted(flags)
    # The handle follows the flag: setListShown re-applies every handle, and the
    # attach runs after the shell build has made listShown current.
    assert re.search(r"C\.splitter\.reapplyAll\(\)", _func_body(js, "setListShown") or "")
    build = js[js.index('id: "agShell"'):]
    assert build.index("applyShell();") < build.index("attachListSplitter(document.getElementById(\"agShell\"))")


def test_p12_agents_rail_attached_in_mountchat_as_ct_split_child():
    """AC-7.1: the rail divider is a child of `.ct-split`, attached by `mountChat`.

    Not of `#ctRail`, whose contents `paintRail2` rebuilds on every `meta`
    event (a handle in it would vanish on the next token). The `.ct-split` is
    new with every chat, so the attach is in `mountChat` and runs each time,
    after the split is in the document.
    """
    js = _agents()
    body = _func_body(js, "mountChat")
    assert body, "no mountChat"
    off, opts = _call_with(body, "agents.rail")
    assert body.count("C.splitter(") == 1
    split = re.search(r"var\s+(\w+)\s*=\s*C\.el\(\s*[\"']div[\"']\s*,\s*\{\s*class\s*:\s*[\"']ct-split[\"']", body)
    assert split, "mountChat no longer builds the .ct-split into a variable"
    name = split.group(1)
    assert re.search(r"\bhost\s*:\s*%s\b" % name, opts), "the host must be the .ct-split element"
    assert re.search(r"\bowner\s*:\s*%s\b" % name, opts)
    assert not re.search(r"\bhost\s*:\s*rail\b", opts) and "ctRail" not in opts
    assert re.search(r"\bpane\s*:\s*rail\b", opts) and re.search(r"\bflexPane\s*:\s*scroll\b", opts)
    assert body.index("body.appendChild(%s)" % name) < off, "attach before the split is in the document"
    for pat in (r"\bdir\s*:\s*-1\b", r"\bcssVar\s*:\s*[\"']rail[\"']", r"\bmin\s*:\s*200\b",
                r"\bmax\s*:\s*520\b", r"\bflexMin\s*:\s*320\b", r"\bkeepWhenCollapsed\s*:\s*true\b",
                r"\bcollapseKey\s*:\s*[\"']agents\.railOff[\"']"):
        assert re.search(pat, opts), "rail splitter lacks %s" % pat
    # The fold is a class on the split (CSS leaves the grid column), read back by collapseGet.
    assert "rail-off" in _func_body(opts, "collapseGet") and "rail-off" in _func_body(opts, "collapseSet")
    # Nothing appends a handle to the rail node.
    assert not re.search(r"\brail\.appendChild\(\s*C\.splitter", js)


def _norm(text):
    return re.sub(r"\s+", " ", text).strip()


def _wide_rules(css):
    """(offset, selector, body) of every leaf rule inside a wide block."""
    out = []
    for s, e in _media_blocks(css, WIDE):
        out += _leaf_rules(css[s:e], base=s)
    return out


def _consumers(css, name):
    """(offset, selector, normalised value) of each wide-block grid-template-columns reading --sp-<name>."""
    hits = []
    for off, sel, body in _wide_rules(css):
        m = re.search(r"grid-template-columns\s*:\s*([^;]*var\(\s*--sp-%s\b[^;]*)" % name, body)
        if m:
            hits.append((off, sel, _norm(m.group(1))))
    return hits


def _narrow(css):
    return [css[s:e] for s, e in _media_blocks(css, "(max-width: 900px)")]


def test_p8_agents_list_consumes_sp_list_with_clamp_fallback():
    """AC-6.2: `var(--sp-list, clamp(208px, 22vw, 302px))` in a wide block, and nothing else changes.

    The fallback is today's fluid default, so with no stored width the shell is
    what it was. The three things that must keep winning are checked here too:
    the fold (`.appshell.hide-list`, more specific), its pinned children, and
    the single column at 900px and under.
    """
    css = _css()
    hits = _consumers(css, "list")
    assert len(hits) == 1, "expected one wide-block consumer of --sp-list, found %d" % len(hits)
    _, sel, val = hits[0]
    assert sel == ".appshell", "--sp-list is read by `%s`" % sel
    m = re.fullmatch(r"var\(--sp-list, (clamp\(208px, 22vw, 302px\))\) 1fr", val)
    assert m, "the clamp fallback is gone: %s" % val
    base = [b for _, s, b in _top_level(css) if s == ".appshell"]
    assert base and m.group(1) in _norm(re.search(r"grid-template-columns\s*:\s*([^;]*)", base[0]).group(1)), (
        "the fallback must equal the base rule's own default")
    wide = {s: b for _, s, b in _wide_rules(css)}
    assert re.search(r"grid-template-columns\s*:\s*0 1fr\b", wide.get(".appshell.hide-list", "")), "the fold column is gone"
    assert "grid-column: 1" in wide.get(".ap-rail", "") and "grid-column: 2" in wide.get(".ap-main", ""), (
        "the pinned children of the folded shell are gone")
    assert any(re.search(r"\.appshell\s*\{\s*grid-template-columns\s*:\s*1fr\s*;", n) for n in _narrow(css)), (
        "the single column at 900px and under is gone")


def test_p8_agents_rail_consumes_sp_rail_after_ct_split_in_its_own_wide_block():
    """AC-5.3 for the rail: read only when wide, after `.ct-split`, folded by a class.

    The first wide block sits above `.ct-split`; a rule there would lose to the
    base rule (equal specificity, later wins), so the consumer needs the block
    that follows the base rule. `position: relative` is the handle's containing
    block. The folded rail leaves the grid, so both children keep their column.
    """
    css = _css()
    hits = _consumers(css, "rail")
    assert len(hits) == 1, "expected one wide-block consumer of --sp-rail, found %d" % len(hits)
    off, sel, val = hits[0]
    assert sel == ".ct-split" and val == "minmax(0, 1fr) var(--sp-rail, 260px)", (sel, val)
    base = [(o, b) for o, s, b in _top_level(css) if s == ".ct-split"]
    assert len(base) == 1, "`.ct-split` must stay one top-level rule"
    boff, bbody = base[0]
    assert re.search(r"\bposition\s*:\s*relative\b", bbody), "`.ct-split` is the handle's containing block"
    assert "minmax(0, 1fr) 260px" in _norm(bbody), "the fallback must equal the base rule's default"
    assert boff < off, "the consumer comes before its base rule"
    assert [s for s, e in _media_blocks(css, WIDE) if s <= off < e][0] > boff, (
        "the consumer sits in a wide block that opens above the base rule")
    wide = {s: _norm(b) for _, s, b in _wide_rules(css)}
    assert re.search(r"grid-template-columns: minmax\(0, 1fr\) 0\b", wide.get(".ct-split.rail-off", "")), "no folded column"
    assert "display: none" in wide.get(".ct-split.rail-off .ct-rail", ""), "a folded rail must leave the grid"
    assert "grid-column: 1" in wide.get(".ct-scroll", "") and "grid-column: 2" in wide.get(".ct-rail", ""), (
        "pin both children, or auto-placement re-seats the transcript")
    narrow = _narrow(css)
    assert any(re.search(r"\.ct-split\s*\{\s*grid-template-columns\s*:\s*1fr\s*;", n) for n in narrow), "stacked layout gone"
    assert any(re.search(r"\.ct-rail\s*>\s*\.ct-panel\s*\{", n) for n in narrow), "the sideways strip rule is gone"


#: The five rail section ids (FR-12): literal, never derived from a title.
_AG_IDS = ["ag.budget", "ag.plan", "ag.todos", "ag.files", "ag.queued"]


def test_p11_ag_ids_once_in_agents_js():
    """AC-12.1 (this file's part): each `ag.*` id appears once in agents.js and in no other script.

    Two sections sharing an id would fold together and share one `panelOpen`
    entry; an id built from a title with a count ("Files touched (3)") would
    forget its state every time the count changed.
    """
    js = _agents()
    for i in _AG_IDS:
        n = len(re.findall(r"[\"']%s[\"']" % re.escape(i), js))
        assert n == 1, "%s appears %d times in agents.js, expected once" % (i, n)
    assert sorted(re.findall(r"[\"'](ag\.[\w-]+)[\"']", js)) == sorted(_AG_IDS), "a stray ag.* id"
    other = "|".join(re.escape(i) for i in _AG_IDS)
    for name in sorted(os.listdir(STATIC)):
        if name.endswith(".js") and name != "agents.js":
            assert not re.search(r"[\"'](%s)[\"']" % other, _read(name)), "%s reuses an ag.* id" % name
    calls = re.findall(r"(?<!function )\brailSection\(\s*(\S)", js)
    assert len(calls) == 5 and set(calls) <= {'"', "'"}, "every railSection id is a string literal"


def test_p11_rail_sections_c_group_ct_panel():
    """AC-12.2 (rail): the five sections are `C.group`s that keep the class `ct-panel`.

    `.ct-rail > .ct-panel` is what lays the rail out as a sideways strip at
    900px and under (CR-21); a `C.group` alone is `.group`, so the class is
    added. Open state is `C.group`'s own, read from storage on every build,
    which is why the rebuild on every `meta` event cannot re-open a fold.
    """
    js = _agents()
    helper = _func_body(js, "railSection")
    assert helper, "no railSection helper"
    assert re.search(r"\bC\.group\(\s*title\s*,\s*kids\s*,\s*\{\s*id\s*:\s*id\s*\}\s*\)", helper), "not a C.group with an id"
    assert re.search(r"classList\.add\(\s*[\"']ct-panel[\"']\s*\)", helper), "ct-panel dropped"
    assert not re.search(r"\bopen\s*:", helper), "sections default open; do not pass `open`"
    sites = re.findall(r"(?<!function )\brailSection\(\s*[\"'](ag\.\w+)[\"']", js)
    assert sorted(sites) == sorted(_AG_IDS), "railSection call sites: %s" % sites
    assert not re.search(r"C\.el\(\s*[\"']section[\"']\s*,\s*\{\s*class\s*:\s*[\"']ct-panel", js), "a raw ct-panel section is left"
    assert any(re.search(r"\.ct-rail\s*>\s*\.ct-panel\s*\{", n) for n in _narrow(_css())), "the strip rule is gone"
    core = _strip_comments(_read("core.js"), line=True)
    assert re.search(r"\bgroup\s*:\s*group\b", core), "C.group is not exported"
    assert not re.search(r"\bcollapsible\s*:\s*collapsible\b", core), "collapsible must stay private (D-12)"


# ---------------------------------------------------------------------------
# The Vault surface (T-037-09..10, slice S3): vault.js and its CSS. The canvas
# is frozen at its pre-drag pixel size while a pane is dragged (resize() writes
# an inline px size), which is the visible price of one reallocation per gesture.
# ---------------------------------------------------------------------------

def _vault():
    return _strip_comments(_read("vault.js"), line=True)


def test_p12_vault_drag_flag_guards_resize():
    """AC-8.1 (D-11): a flag makes `resize()` wait during a drag; the release runs it once.

    The ResizeObserver fires on every frame of a pane drag and `resize()`
    reallocates both canvases, so without the flag a drag is a canvas
    reallocation per frame. The three `setTimeout(resize, 60)` and the observer
    stay as they were: the flag is the only change to the redraw path.
    """
    js = _vault()
    body = _func_body(js, "resize")
    assert body, "no resize()"
    assert re.match(r"\s*if\s*\(\s*paneDragging\s*\)\s*return\s*;", body), (
        "the drag flag must be the FIRST statement of resize()")
    assert len(re.findall(r"\bvar\s+paneDragging\s*=\s*false\s*;", js)) == 1
    assert len(re.findall(r"\bpaneDragging\b", js)) == 4, "the flag is declared, tested, set and cleared: once each"
    start, end = _func_body(js, "paneDragStart"), _func_body(js, "paneDragEnd")
    assert start is not None and re.fullmatch(r"\s*paneDragging\s*=\s*true\s*;\s*", start), (
        "paneDragStart must only set the flag (no resize() during a drag)")
    assert end is not None and re.fullmatch(r"\s*paneDragging\s*=\s*false\s*;\s*resize\(\)\s*;\s*", end), (
        "paneDragEnd must clear the flag, then call resize() once")
    for fn, key in (("attachSideSplitter", "vault.side"), ("attachViewerSplitter", "vault.viewer")):
        opts = _call_with(_func_body(js, fn) or "", key)[1]
        assert re.search(r"\bonDragStart\s*:\s*paneDragStart\b", opts), "%s lacks onDragStart" % key
        assert re.search(r"\bonDragEnd\s*:\s*paneDragEnd\b", opts), "%s lacks onDragEnd" % key
    assert len(re.findall(r"setTimeout\(\s*resize\s*,\s*60\s*\)", js)) == 3, "the three deferred resizes changed"
    observer = r"new\s+ResizeObserver\(\s*function\s*\(\)\s*\{\s*resize\(\)\s*;\s*\}\s*\)\s*\.observe\(\s*stage\s*\)"
    assert len(re.findall(observer, js)) == 1, "the ResizeObserver changed"


def test_p12_vault_handles_on_vault_not_stage():
    """AC-8.2: both handles are children of `.vault`; the viewer's lives only while a file is open.

    `.vault-stage` clips (overflow hidden) and owns the canvas mouse handlers, so a
    handle in it would be cut off or fight the graph's own pointer code. The
    viewer's handle follows `.has-viewer`, and since nothing tells the splitter a
    handle left, closing the viewer re-applies every handle right after.
    """
    js = _vault()
    assert len(_splitter_calls(js)) == 2 and js.count("C.splitter(") == 2, "expected exactly two Vault handles"
    assert re.search(r"class\s*:\s*[\"']vault[\"']\s*,\s*id\s*:\s*[\"']vaultWrap[\"']", js), "`.vault` is no longer #vaultWrap"
    parts = {}
    for fn, key, pane, cssvar, dr in (("attachSideSplitter", "vault.side", "vaultSide", "side", "1"),
                                      ("attachViewerSplitter", "vault.viewer", "vaultViewer", "viewer", "-1")):
        assert re.search(r"function\s+%s\s*\(\s*wrap\s*\)" % fn, js), "%s no longer takes the .vault element" % fn
        opts = parts[key] = _call_with(_func_body(js, fn), key)[1]
        assert re.search(r"\bhost\s*:\s*wrap\s*,", opts) and re.search(r"\bowner\s*:\s*wrap\s*,", opts), (
            "%s: the host and the variable owner must be .vault" % key)
        assert re.search(r"\bpane\s*:\s*document\.getElementById\(\s*[\"']%s[\"']\s*\)" % pane, opts), key
        assert re.search(r"\bflexPane\s*:\s*document\.getElementById\(\s*[\"']vaultStage[\"']\s*\)\s*,\s*flexMin\s*:\s*200\b", opts), (
            "%s: the stage is the flexible pane, never the host (minimum 200)" % key)
        assert re.search(r"\bcssVar\s*:\s*[\"']%s[\"']" % cssvar, opts) and re.search(r"\bdir\s*:\s*%s\b" % dr, opts), key
        for field in re.findall(r"\b(?:host|owner|pane)\s*:[^,]*,", opts):
            assert "vaultStage" not in field, "%s: the stage is never the host, owner or measured pane" % key
    assert re.search(r"\bmin\s*:\s*200\b.*?\bmax\s*:\s*480\b", parts["vault.side"], re.S)
    assert re.search(r"\bmin\s*:\s*280\b.*?\bmax\s*:\s*720\b", parts["vault.viewer"], re.S)
    side = parts["vault.side"]
    assert re.search(r"\bcollapseKey\s*:\s*[\"']vault\.sideOff[\"']", side) and re.search(r"\bkeepWhenCollapsed\s*:\s*true\b", side)
    assert "side-off" in _func_body(side, "collapseGet") and "side-off" in _func_body(side, "collapseSet")
    assert not re.search(r"collapse|keepWhenCollapsed", parts["vault.viewer"]), "the viewer closes with its X, not a fold"
    # The sidebar's handle is attached by render, after the stage is wired and before the first resize().
    render = _func_body(js, "render")
    wired = render.index("wireStage();")
    assert wired < render.index("attachSideSplitter(") < render.index("resize();", wired)
    assert "attachSideSplitter(document.getElementById(\"vaultWrap\"))" in render
    # The viewer's handle follows .has-viewer: attached once opened, removed once closed.
    opening = _func_body(js, "openViewer")
    assert opening.index('classList.add("has-viewer")') < opening.index("attachViewerSplitter(wrap)")
    assert opening.count("attachViewerSplitter(") == 1 and "var wrap = document.getElementById(\"vaultWrap\")" in opening
    removals = [m.start() for m in re.finditer(r"classList\.remove\(\s*[\"']has-viewer[\"']\s*\)", js)]
    assert len(removals) == 1 and re.match(r"[^;]*;\s*detachViewerSplitter\(\)\s*;", js[removals[0]:]), (
        "the viewer must lose its handle where it loses .has-viewer")
    assert "viewerSplit.isConnected" in _func_body(js, "attachViewerSplitter"), "a second open must not add a second handle"
    assert re.search(r"C\.splitter\.reapplyAll\(\)\s*;\s*$", _func_body(js, "attachViewerSplitter"))
    gone = _func_body(js, "detachViewerSplitter")
    assert gone.index("removeChild(") < gone.index("C.splitter.reapplyAll()"), "reapplyAll must follow the removal"


def _vault_columns(val, root):
    """A consumer's column list with the `--sp-*` fallbacks and `--vault-*` tokens resolved to px."""
    val = re.sub(r"var\(--sp-(?:side|viewer),\s*(var\(--vault-[a-z]+\)|\d+px)\)", r"\1", val)
    return _norm(re.sub(r"var\((--vault-(?:side|viewer))\)", lambda m: root[m.group(1)], val))


def test_p8_vault_consumes_sp_side_and_sp_viewer_after_its_base_rules():
    """AC-5.3 for the Vault: read only when wide, after `.vault`, fallbacks equal today's 262px / 400px.

    The first wide block sits above `.vault`; a consumer there would lose to the
    base rule (equal specificity, later wins). A folded sidebar leaves the grid
    (`display: none`), so all three children are pinned to their own column and
    the stage spans the sidebar's track: auto-placement would otherwise seat the
    stage in column 1. The trims at 900px and under must keep winning, so the
    pins and the fold exist only in the wide block.
    """
    css = _css()
    top = _top_level(css)
    base = {s: (o, _norm(b)) for o, s, b in top if s in (".vault", ".vault.has-viewer")}
    assert sorted(base) == [".vault", ".vault.has-viewer"], "a base rule moved or was duplicated"
    root = {}
    for _, s, b in top:
        if s == ":root":
            root.update(re.findall(r"(--vault-(?:side|viewer))\s*:\s*([^;]+);", b))
    root = {k: v.strip() for k, v in root.items()}
    assert root == {"--vault-side": "262px", "--vault-viewer": "400px"}, root
    assert "var(--vault-side) minmax(0, 1fr) 0" in base[".vault"][1]
    assert "var(--vault-side) minmax(0, 1fr) var(--vault-viewer)" in base[".vault.has-viewer"][1]
    assert re.search(r"\bposition\s*:\s*relative\b", base[".vault"][1]), "`.vault` is the handles' containing block"
    side, viewer = _consumers(css, "side"), _consumers(css, "viewer")
    assert [s for _, s, _ in side] == [".vault", ".vault.has-viewer"], "--sp-side consumers: %s" % [s for _, s, _ in side]
    assert [s for _, s, _ in viewer] == [".vault.has-viewer"], "--sp-viewer consumers: %s" % [s for _, s, _ in viewer]
    want = {".vault": "262px minmax(0, 1fr) 0", ".vault.has-viewer": "262px minmax(0, 1fr) 400px"}
    for off, sel, val in side + viewer:
        assert base[sel][0] < off, "`%s` consumer comes before its base rule" % sel
        assert _vault_columns(val, root) == want[sel], "`%s` fallback is not today's value: %s" % (sel, val)
    wide = {s: _norm(b) for _, s, b in _wide_rules(css)}
    for sel, col in ((".vault-side", "1"), (".vault-stage", "2"), (".vault-viewer", "3")):
        assert re.fullmatch(r"grid-column: %s;?" % col, wide.get(sel, "")), "`%s` is not pinned to column %s" % (sel, col)
        assert not [b for _, s, b in top if sel in _parts(s) and "grid-column" in b], (
            "a pin outside the wide block would invent a column in the single-column layouts")
    assert "display: none" in wide.get(".vault.side-off .vault-side", ""), "a folded sidebar must leave the grid"
    assert re.fullmatch(r"grid-column: 1 / 3;?", wide.get(".vault.side-off .vault-stage", "")), "the stage must take the folded track"
    assert not [s for _, s, _ in top if "side-off" in s], "the fold exists only in the wide block"
    narrow = "\n".join(_narrow(css))
    assert re.search(r":root\s*\{\s*--vault-side\s*:\s*218px\s*;\s*\}", narrow), "the 218px sidebar trim is gone"
    assert re.search(r"\.vault\.has-viewer\s*\{\s*grid-template-columns\s*:\s*var\(--vault-side\)\s+minmax\(0,\s*1fr\)\s+0\s*;", narrow), (
        "the viewer overlay's columns at 900px and under are gone")
    phone = "\n".join(css[s:e] for s, e in _media_blocks(css, "(max-width: 720px)"))
    assert re.search(r"\.vault\s*\{\s*grid-template-columns\s*:\s*1fr\s*;", phone), "the phone layout is gone"


#: The four sidebar card ids (FR-12) and their defaults: today's look is kept.
_VAULT_IDS = ["vault.filters", "vault.display", "vault.forces", "vault.navigator"]
_VAULT_OPEN = {"vault.filters": True, "vault.display": False, "vault.forces": False, "vault.navigator": True}


def test_p11_vault_ids_literal_once():
    """AC-12.1 (vault part): each `vault.*` card id is a literal, once in vault.js and in no other script.

    `panelOpen` is one flat map for the whole console, so an id shared with
    another section would fold both; an id built from a label would change
    with the label. The handles' own layout keys (`vault.side`, `vault.viewer`,
    `vault.sideOff`) live in `layout`, not here, and are the only other
    `vault.` strings the file may hold.
    """
    js = _vault()
    for i in _VAULT_IDS:
        n = len(re.findall(r"[\"']%s[\"']" % re.escape(i), js))
        assert n == 1, "%s appears %d times in vault.js, expected once" % (i, n)
    keys = {"vault.side", "vault.viewer", "vault.sideOff"}
    stray = set(re.findall(r"[\"'](vault\.[\w-]+)[\"']", js)) - keys
    assert sorted(stray) == sorted(_VAULT_IDS), "a stray vault.* string: %s" % sorted(stray - set(_VAULT_IDS))
    cards = re.search(r"\bvar\s+CARDS\s*=\s*\[(.*?)\]\s*;", js, re.S).group(1)
    assert re.findall(r"\bid\s*:\s*[\"']([\w.]+)[\"']", cards) == _VAULT_IDS, "CARDS ids are not the four literals"
    assert len(re.findall(r"\bid\s*:", cards)) == 4, "an id in CARDS is not a string literal"
    other = "|".join(re.escape(i) for i in _VAULT_IDS)
    for name in sorted(os.listdir(STATIC)):
        if name.endswith(".js") and name != "vault.js":
            assert not re.search(r"[\"'](%s)[\"']" % other, _read(name)), "%s reuses a vault.* id" % name


def test_p11_vault_cards_use_panelopen():
    """AC-12.2 (vault part): card state lives in `panelOpen`, read at every build, no map of its own.

    The `.vault-card` markup stays (no `C.panel` swap), so the one thing that
    moves is where "open" is kept: the same preference object core.js's
    collapsible() reads and writes, with the same rule (an own key wins, else
    the card's default). `st.openCards` was memory only and forgot every fold on
    a tab switch.
    """
    raw = _read("vault.js")
    assert "openCards" not in raw, "st.openCards (or a mention of it) is still in vault.js"
    assert "localStorage" not in raw, "cards must go through C.prefs, not localStorage"
    js = _vault()
    assert js.count('C.prefs.get("panelOpen"') == 1 and js.count('C.prefs.set("panelOpen"') == 1, (
        "panelOpen is read in one helper and written in one")
    mapper = _func_body(js, "panelMap") or ""
    assert 'C.prefs.get("panelOpen"' in mapper, "the read is not in panelMap()"
    assert re.search(r"typeof\s+map\s*===\s*[\"']object[\"']", mapper) and "Array.isArray(map)" in mapper, (
        "panelMap must ignore a stored value that is not a plain object")
    reader, writer = _func_body(js, "cardOpen") or "", _func_body(js, "setCardOpen") or ""
    assert "panelMap()" in reader and re.search(r"hasOwnProperty\.call\(\s*map\s*,\s*def\.id\s*\)", reader), "cardOpen lost the own-key rule"
    assert re.search(r"\bdef\.open\s*!==\s*false\b", reader), "cardOpen lost the per-card default"
    assert re.search(r"\bmap\[\s*def\.id\s*\]\s*=\s*!!on\s*;", writer) and 'C.prefs.set("panelOpen", map)' in writer, "setCardOpen"
    card = _func_body(js, "card") or ""
    assert re.search(r"\bvar\s+open\s*=\s*cardOpen\(\s*def\s*\)\s*;", card), "the state is not read at build"
    toggle = re.search(r"onclick\s*:\s*function\s*\(\)\s*\{(.*?)\},\s*\}", card, re.S)
    assert toggle and re.match(r"\s*setCardOpen\(\s*def\s*,\s*!\s*cardOpen\(\s*def\s*\)\s*\)\s*;\s*paintSidebar\(\)", toggle.group(1)), (
        "a click must write through setCardOpen and then repaint")
    assert not re.search(r"\bst\.\w*[Cc]ard", js), "a card state map on st"
    for cls in ("vault-card", "vault-card-h", "vault-card-b"):
        assert re.search(r"[\"']%s[\"' ]" % cls, js), "the .%s markup is gone" % cls
    assert not re.search(r"\bC\.(panel|group)\(", js), "the cards keep their own markup (D-12)"
    cards = re.search(r"\bvar\s+CARDS\s*=\s*\[(.*?)\]\s*;", js, re.S).group(1)
    defaults = {k: v == "true" for k, v in re.findall(r"\bid\s*:\s*\"(vault\.\w+)\"[^}]*?\bopen\s*:\s*(true|false)", cards)}
    assert defaults == _VAULT_OPEN, "defaults changed (Filters and Navigator open, Display and Forces closed): %s" % defaults


# ---------------------------------------------------------------------------
# S4: board lanes (T-037-11, T-037-12)
# ---------------------------------------------------------------------------

def _board():
    return _strip_comments(_read("board.js"), line=True)


def test_p8_lane_consumes_sp_lane_after_its_base_rule_with_lane_w_fallback():
    """AC-9.1 (CSS half): `.lane` reads `var(--sp-lane, var(--lane-w))` in a wide block placed after `.lane`.

    The fallback keeps today's 270px and the 1280px trim (`:root { --lane-w: 252px }`)
    for a user with no stored width; `.lane.cold` keeps 52px (more specific); the
    720px `.lane` rule still wins below the wide query; `.lane` is the handle's
    containing block through CSS.
    """
    css = _css()
    top = _top_level(css)
    base = [(o, _norm(b)) for o, s, b in top if s == ".lane"]
    assert len(base) == 1, "`.lane` is defined %d times at top level" % len(base)
    assert "flex: 0 0 var(--lane-w)" in base[0][1] and "max-width: var(--lane-w)" in base[0][1]
    assert re.search(r"\bposition\s*:\s*relative\b", base[0][1]), "`.lane` is the handle's containing block"
    hits = [(o, s, _norm(b)) for o, s, b in _wide_rules(css) if "--sp-lane" in b]
    assert [s for _, s, _ in hits] == [".lane"], "--sp-lane consumers: %s" % [s for _, s, _ in hits]
    off, _, body = hits[0]
    assert off > base[0][0], "the consumer comes before the `.lane` base rule"
    want = "var(--sp-lane, var(--lane-w))"
    assert re.search(r"flex-basis: %s" % re.escape(want), body) and re.search(r"max-width: %s" % re.escape(want), body), body
    assert css.count("--sp-lane") == 2, "--sp-lane appears outside the one consumer"
    cold = [_norm(b) for _, s, b in top if s == ".lane.cold"]
    assert len(cold) == 1 and "flex-basis: 52px" in cold[0] and "max-width: 52px" in cold[0] and "--sp-" not in cold[0]
    assert not [b for _, s, b in top if s == ".lanes" and "--sp-" in b], "the owner only carries the variable inline"
    assert re.search(r":root\s*\{\s*--lane-w\s*:\s*252px\s*;\s*\}", css), "the 1280px trim is gone"
    phone = "\n".join(css[s:e] for s, e in _media_blocks(css, "(max-width: 720px)"))
    assert re.search(r"\.lane\s*\{[^}]*flex-basis\s*:\s*min\(300px,\s*86vw\)", phone), "the 720px lane rule is gone"


def test_p12_board_lane_handle_attach():
    """AC-9.1 (JS half): one handle per open lane, host = the lane, owner = `.lanes` through a function.

    Wrong ways: a handle on the cold rail, the same ordinal on every lane (the
    edge would outrun the pointer), every handle primary (a Tab stop per lane),
    attaching without ever calling `reapplyAll()` after the mount (the width is
    never put on the new `.lanes`), or a `draggable` handle (it would fight the
    cards' HTML5 drag-and-drop).
    """
    js = _board()
    assert js.count("C.splitter(") == 1, "one attach, inside laneNode"
    _, opts = _call_with(js, "board.lane")
    for pat in (r"\bcssVar\s*:\s*[\"']lane[\"']", r"\bmin\s*:\s*200\b", r"\bmax\s*:\s*480\b",
                r"\bhost\s*:\s*node\b", r"\bpane\s*:\s*node\b", r"\bordinal\s*:\s*ctx\.n\b",
                r"\bprimary\s*:\s*ctx\.n\s*===\s*1\b", r"\bowner\s*:\s*function\s*\(\)\s*\{\s*return\s+ctx\.lanes\s*;"):
        assert re.search(pat, opts), "lane splitter lacks %s" % pat
    for banned in ("collapseSet", "collapseKey", "draggable", "dir", "270"):
        assert not re.search(r"\b%s\b" % banned, opts), "lane splitter must not carry %s" % banned
    node = _func_body(js, "laneNode") or ""
    at = node.index("C.splitter(")
    guard = node[:at].rstrip()
    assert re.search(r"if\s*\(\s*!cold\s*&&\s*ctx\s*\)\s*\{\s*ctx\.n\s*\+=\s*1\s*;$", guard), "the attach must be guarded by !cold and count open lanes"
    assert "draggable" not in js[js.index("function laneNode"):js.index("function moveTicket")].replace('ondragover', ""), "the lane code gained draggable"
    paint = _func_body(js, "paint") or ""
    assert re.search(r"var\s+ctx\s*=\s*\{\s*n\s*:\s*0\s*,\s*lanes\s*:\s*lanes\s*\}", paint)
    assert re.search(r"laneNode\(\s*l\s*,\s*ctx\s*\)", paint)
    assert paint.index("shell.appendChild(lanes)") < paint.index("C.splitter.reapplyAll()"), "reapplyAll before the mount"
    assert paint.count("C.splitter.reapplyAll()") == 1


def test_p12_every_lane_handle_carries_the_shared_width():
    """Browser finding: the non-primary lane handles had no `aria-valuenow`.

    `mark()` must not return early for a non-primary handle, and `refresh()` must
    bring every handle with the same `key` up to date (they share one width), so
    a drag on lane 3 also moves the value on lane 1 and 2. Wrong ways: the early
    `if (!e.primary) return;` comes back, or refresh touches only the dragged one.
    """
    js = _js()
    mark = _func_body(js, "mark") or ""
    assert "aria-valuenow" in mark and "primary" not in mark, "mark() must set the value on every handle"
    refresh = _func_body(js, "refresh") or ""
    assert re.search(r"registry\.forEach", refresh) and re.search(r"opts\.key\s*===\s*e\.opts\.key", refresh), (
        "refresh() must reach the handles that share e's key")
    assert re.search(r"(?<![\w.])mark\(e\)", refresh), "the dragged handle itself must still be refreshed"


_OV_IDS = ["ov.glance", "ov.attention", "ov.flow", "ov.recent", "ov.jobs", "ov.schedules"]
_AS_IDS = ["as.talk", "as.runs", "as.tickets"]


def test_p11_section_ids_unique_and_scoped():
    """AC-12.1 final: the 18 ids each appear once in their own file and in no other script.

    One flat `panelOpen` map: a reused id folds two sections together. The
    Getting-started card is not one of them (`ov.onboarding` stays absent).
    """
    own = {"overview.js": _OV_IDS, "assistant.js": _AS_IDS, "agents.js": _AG_IDS, "vault.js": _VAULT_IDS}
    every = [i for ids in own.values() for i in ids]
    assert len(every) == 18 and len(set(every)) == 18
    pattern = "|".join(re.escape(i) for i in every)
    for name in sorted(os.listdir(STATIC)):
        if not name.endswith(".js"):
            continue
        src = _read(name)
        found = re.findall(r"[\"'](%s)[\"']" % pattern, src)
        assert sorted(found) == sorted(own.get(name, [])), "%s holds the wrong section ids: %s" % (name, found)
    for name in ("overview.js", "assistant.js"):
        src = _read(name)
        prefix = "ov" if name == "overview.js" else "as"
        assert sorted(re.findall(r"[\"'](%s\.[\w-]+)[\"']" % prefix, src)) == sorted(own[name]), "stray id in " + name
        assert len(re.findall(r"\bcollapse\s*:\s*\{\s*id\s*:\s*[\"']", src)) == len(own[name]), "a non-literal id in " + name
    assert not re.findall(r"[\"'](?!set\.)[a-z]+\.[\w-]+[\"']\s*,\s*open", _read("settings.js")), "settings ids must stay set.*"


def test_p11_overview_enter_guard():
    """AC-12.2 / D-14: Enter on the Needs-attention header folds without opening a row.

    The header toggles on Enter (core.js) and the keydown then bubbles to the
    panel handler, which used to click the highlighted row on any Enter.
    """
    js = _read("overview.js")
    at = js.index('attnPanel.addEventListener("keydown"')
    handler = js[at:js.index("grid.appendChild", at)]
    click = handler.index("rows[idx].click()")
    guard = handler[:click]
    assert re.search(r"e\.target\.closest\(\s*[\"']header[\"']\s*\)", guard), "no header-target guard before the click"
    assert re.search(r"attnPanel\.classList\.contains\(\s*[\"']collapsed[\"']\s*\)", guard), "no collapsed guard before the click"
    assert "onboardingOpen" in js and "Open setup" in js and "hideOnboarding" in js, "the Getting-started card changed"
    assert "ov.onboarding" not in js


def test_p13_foldbar_used_on_overview_and_assistant_only():
    """AC-13.1: the fold bar is the first row of the Overview and Assistant hosts; Settings keeps its jump bar."""
    for name in ("overview.js", "assistant.js"):
        js = _read(name)
        assert len(re.findall(r"host\.appendChild\(\s*C\.splitter\.foldBar\(\s*host\s*\)\s*\)", js)) == 1, name
    ov = _read("overview.js")
    assert ov.index("C.splitter.foldBar(host)") < ov.index("grid.appendChild(onboardingCard("), "the bar is not before the grid"
    asst = _read("assistant.js")
    assert asst.index("C.splitter.foldBar(host)") < asst.index('class: "grid as-home"'), "the bar is not before the grid"
    for name in sorted(os.listdir(STATIC)):
        if name.endswith(".js") and name not in ("overview.js", "assistant.js", "splitter.js"):
            assert "foldBar(" not in _read(name), "%s uses foldBar" % name


def test_p14_layoutpanel_one_function_one_push():
    """AC-14.1: one layoutPanel() in Settings, pushed once next to storage; set.layout once."""
    js = _strip_comments(_read("settings.js"), line=True)
    assert len(re.findall(r"function\s+layoutPanel\s*\(", js)) == 1
    pushes = re.findall(r"kids\.push\(\s*layoutPanel\(", js)
    assert len(pushes) == 1, "layoutPanel is not pushed exactly once"
    assert re.search(r"kids\.push\(\s*storage\([^)]*\)\s*\);\s*kids\.push\(\s*layoutPanel\(\s*\)\s*\);", js), \
        "the push is not next to the storage push"
    assert js.count('"set.layout"') == 1
    assert "foldBar" not in js
    # the other tickets' markers survive
    assert "Run setup again" in js and "function identity(" in js and "kids.push(identity(" in js


def test_p14_reset_three_prefs_del_no_localstorage_no_prefs_reset():
    """AC-14.2 / 15.2 / D-15: exactly the three keys are removed, nothing else."""
    js = _strip_comments(_read("settings.js"), line=True)
    body = _func_body(js, "layoutPanel")
    assert body is not None
    assert re.findall(r"C\.prefs\.del\(\s*[\"']([^\"']+)[\"']\s*\)", body) == ["layout", "panelOpen", "chatListHidden"]
    assert body.count("C.prefs.") == 3, "layoutPanel touches prefs beyond the three deletes"
    assert "localStorage" not in body and "C.prefs.reset" not in body
    assert "reapplyAll()" in body
    assert re.search(r"ConsoleApp\.go\(", body) and "C.toast(" in body
    assert "localStorage" not in _read("splitter.js")


# ---------------------------------------------------------------------------
# T-037 S7a: the docked ticket panel (C10). P-10 first half, dock rows of P-8.
# ---------------------------------------------------------------------------

def _drawer_iife():
    """The drawer IIFE, cut by its anchors (never by line number), comments blanked."""
    js = _strip_comments(_read("app.js"), line=True)
    a = js.index("var drawer = (function")
    b = js.index("})();", a)
    return js[a:b + 5]


def test_p10_drawer_export_shape_single_opener():
    """AC-10.1: the IIFE exports exactly {open, close}; drawer.open( lives only in board.js."""
    code = _drawer_iife()
    assert re.search(r"return\s*\{\s*open:\s*open,\s*close:\s*close\s*\}\s*;", code)
    openers = [n for n in sorted(os.listdir(STATIC)) if n.endswith(".js")
               and re.search(r"\bdrawer\.open\(", _strip_comments(_read(n), line=True))]
    assert openers == ["board.js"], openers


def test_p10_dockmode_single_uses_wide_roles_flip():
    """AC-10.2: one dockMode() on C.splitter.WIDE; both roles, flipped on a live switch; one flagged change listener."""
    code = _drawer_iife()
    assert len(re.findall(r"function\s+dockMode\s*\(", code)) == 1
    body = _func_body(code, "dockMode")
    assert "C.splitter.WIDE" in body and "matchMedia" in body
    assert "901px" not in code and "900px" not in code
    mount = _func_body(code, "mount")
    assert mount is not None
    assert '"complementary"' in mount and '"dialog"' in mount
    assert re.search(r"removeAttribute\(\s*[\"']aria-modal[\"']", mount)
    assert re.search(r"setAttribute\(\s*[\"']aria-modal[\"']", mount)
    assert "dockMode()" in code and "mount(dockMode())" in code
    # the scrim exists only on the modal branch of mount()
    assert mount.count("class: \"scrim\"") == 1 and "scrim" not in _func_body(code, "dockMode")
    # one listener install, behind a once-flag, never per open
    assert len(re.findall(r"addEventListener\(\s*[\"']change[\"']", code)) == 1
    assert re.search(r"if\s*\(\s*!modeBound\s*\)\s*\{\s*modeBound\s*=\s*true", code)
    assert "modeBound" not in (_func_body(code, "close") or "")


def test_p10_resize_resyncs_dock_mode_f8():
    """F-8 (source-level only; no JS runner): a window resize re-checks dockMode() and re-mounts on a flip.

    A live browser run left has-dock/role/scrim stale after 901 -> 900 px, so the
    media-query `change` event is backed by a `resize` listener sharing one `sync`.
    mount() (the single place that sets class, role, aria-modal, scrim) is reused,
    so the panel node is moved, never rebuilt. Behaviour needs a browser check.
    """
    code = _drawer_iife()
    m = re.search(r"var\s+sync\s*=\s*function\s*\(\s*\)\s*\{(.*?)\};", code, re.S)
    assert m, "no shared sync()"
    s = _norm(m.group(1))
    assert "panel" in s and "docked !== dockMode()" in s and "mount(dockMode())" in s
    assert re.search(r"addEventListener\(\s*[\"']change[\"']\s*,\s*sync\s*\)", code)
    assert re.search(r"window\.addEventListener\(\s*[\"']resize[\"']\s*,\s*sync\s*\)", code)
    assert len(re.findall(r"addEventListener\(\s*[\"']resize[\"']", code)) == 1
    assert "901px" not in code and "900px" not in code


def test_p10_dock_handle_goes_through_splitter_registry():
    """FR-5 `dock.w`: host=pane=aside, owner=#app, no collapse; close() lets the registry prune."""
    code = _drawer_iife()
    calls = _splitter_calls(code)
    assert len(calls) == 1, "expected exactly one C.splitter( call in the drawer"
    call = _norm(calls[0][1])
    for want in ('cssVar: "dock"', 'key: "dock.w"', "min: 320", "max: 720", "flexMin: 360",
                 "dir: -1", "host: panel", "pane: panel", "owner: app",
                 'label: "Resize ticket panel"'):
        assert want in call, want
    assert "collapse" not in call
    assert "430" not in code, "the default width lives in CSS only"
    assert "reapplyAll()" in _func_body(code, "close")
    assert "reapplyAll()" in _func_body(code, "mount")
    assert "grid-template-columns" not in code and "documentElement" not in code


def _dock_rules(css):
    """Wide-block leaf rules whose selector mentions .has-dock."""
    return [r for r in _wide_rules(css) if ".has-dock" in r[1]]


def test_p8_dock_vars_in_wide_block_after_drawer_rules():
    """AC-5.3/5.4 for --sp-dock: consumed only in the wide dock block, 430px fallback, after .drawer .dbody."""
    css = _css()
    uses = [m.start() for m in re.finditer(r"--sp-dock", css)]
    assert uses, "--sp-dock is never consumed"
    wide_spans = _media_blocks(css, WIDE)
    for u in uses:
        assert any(s <= u < e for s, e in wide_spans), "--sp-dock outside a wide block"
    cons = _consumers(css, "dock")
    assert len(cons) == 1 and cons[0][1] == "#app.has-dock"
    assert cons[0][2] == "minmax(0, 1fr) var(--sp-dock, 430px)"
    assert css.index(".drawer .dbody {") < cons[0][0]
    assert css.index(".drawer {") < cons[0][0]
    # nothing else writes it: not :root/html, and never a transition on the columns
    assert not re.search(r"(:root|html)[^{}]*\{[^{}]*--sp-dock", css)
    assert not re.search(r"transition[^;{}]*grid-template-columns", css)


def test_p8_dock_block_places_aside_as_relative_grid_child():
    """CR-27/CR-25: the docked aside is relative (never static), a grid child, min 0; topbar spans; no .scrim."""
    css = _css()
    rules = _dock_rules(css)
    by = {sel: body for _, sel, body in rules}
    aside = _norm(by.get("#app.has-dock > .drawer", ""))
    assert aside, "no #app.has-dock > .drawer rule in a wide block"
    assert "position: relative" in aside and "static" not in aside
    assert "grid-column: 2" in aside and "grid-row: 2" in aside
    assert "min-width: 0" in aside and "min-height: 0" in aside
    assert re.search(r"z-index:\s*auto", aside) and "animation: none" in aside
    assert "grid-column: 1 / -1" in _norm(by.get("#app.has-dock > .topbar", ""))
    assert not any("scrim" in sel for _, sel, _ in rules)
    # the dock rules sit after every base rule they override
    first = min(off for off, _, _ in rules)
    for base in (".drawer {", ".drawer .dbody {", "#app {", ".topbar {"):
        assert css.index(base) < first, base
    # no top-level `#app.has-dock` rule outside a wide block (narrow stays modal)
    for off, sel, _ in _top_level(css):
        assert ".has-dock" not in sel, "has-dock rule outside the wide block"


# ---------------------------------------------------------------------------
# T-037 S7b: dock behaviour and print (C10). P-10 second half, dock rows of P-8.
# Structural proxies only: no JS runner exists. Real focus, Esc, refresh and
# print feel are the [BROWSER] checks (AC-11.3, 11.4, 11.6).
# ---------------------------------------------------------------------------

def test_p10_repeat_open_swaps_in_fresh_dbody_listeners_once():
    """AC-11.1 (D-9): a repeat open() refreshes in place with a NEW .dbody and returns it."""
    code = _drawer_iife()
    opn, ref = _func_body(code, "open"), _func_body(code, "refresh")
    assert opn is not None and ref is not None
    # the repeat branch comes first in open(), before anything that builds or moves the aside
    assert re.match(r"\s*if\s*\(\s*panel\s*\)\s*return\s+refresh\(", opn)
    assert 'C.el("div", { class: "dbody" })' in ref
    assert re.search(r"panel\.replaceChild\(\s*body\s*,\s*old\s*\)", ref)
    assert re.search(r"return\s+body\s*;", ref) and re.search(r"return\s+body\s*;", opn)
    # in place: no close, no new aside, no re-mount, restore target and listeners untouched
    for bad in ("close(", 'C.el("aside"', "mount(", "lastFocus", "addEventListener", "appendChild(panel"):
        assert bad not in ref, "refresh() must not use " + bad
    assert opn.count('C.el("aside"') == 1 and "close();" not in opn
    assert "aria-label" in ref
    # one keydown install (balanced by one remove in close) and one change install, flag-guarded
    assert len(re.findall(r"document\.addEventListener\(\s*[\"']keydown[\"']", code)) == 1
    assert len(re.findall(r"document\.removeEventListener\(\s*[\"']keydown[\"']", code)) == 1
    assert "removeEventListener" in _func_body(code, "close")
    assert len(re.findall(r"addEventListener\(\s*[\"']change[\"']", code)) == 1
    assert opn.index("addEventListener(\"keydown\"") > opn.index('C.el("aside"')


def test_p10_escape_when_docked_needs_the_target_inside_the_panel():
    """D-10: modal Esc closes anywhere; docked Esc closes only from inside; stopPropagation only when it acts."""
    code = _drawer_iife()
    on = _norm(_func_body(code, "onKey"))
    assert 'e.key !== "Escape"' in on
    guard = re.search(r"if \(docked && !\(panel && panel\.contains\(e\.target\)\)\) return;", on)
    assert guard, "docked Esc must be conditioned on panel.contains(e.target)"
    assert on.index("return;", guard.start()) < on.index("e.stopPropagation()") < on.index("close()")
    assert re.search(r"\bdocked\s*=\s*isDocked\s*;", _func_body(code, "mount"))
    assert re.search(r"\bdocked\s*=\s*false\s*;", _func_body(code, "close"))


def _print_blocks(css):
    return [css[s:e] for s, e in _media_blocks(css, "print")]


def test_p10_every_print_block_covers_dock():
    """AC-11.2 (CR-31): the dock's column is taken back in print, after the dock block; the shared rule still hides .drawer."""
    css = _css()
    blocks = _print_blocks(css)
    dock = [b for b in blocks if "#app.has-dock" in b]
    assert len(dock) == 1, "expected one @media print block that names #app.has-dock"
    assert _norm(dock[0]).replace(" ", "") == "#app.has-dock{grid-template-columns:minmax(0,1fr);}"
    assert not re.search(r"\.drawer|\.scrim|display", dock[0]), "this block only resets the grid"
    # later in source than the wide dock rule (same specificity, later wins) and mid-file
    at = css.index(dock[0])
    assert at > css.index("#app.has-dock { grid-template-columns: minmax(0, 1fr) var(--sp-dock")
    assert css.count("\n", 0, at) < 0.85 * css.count("\n")
    # the shared print rule still hides the aside; the docked aside rule sets no display to fight it
    shared = [b for b in blocks if ".drawer" in b and "display: none !important" in b]
    assert len(shared) == 1 and re.search(r"\.drawer\b", shared[0].split("{")[0])
    aside = [b for _, sel, b in _dock_rules(css) if sel == "#app.has-dock > .drawer"]
    assert aside and "display" not in aside[0]


def test_p10_listeners_flag_and_index_html_only_gains_the_splitter_tag():
    """AC-5.3 dock rows + index.html: the change listener is flag-guarded; one splitter tag, onboarding tag untouched."""
    code = _drawer_iife()
    assert re.search(r"if\s*\(\s*!modeBound\s*\)", _func_body(code, "open"))
    srcs = _script_srcs(_read("index.html"))
    assert srcs.count("splitter.js") == 1 and srcs.count("onboarding-wizard.js") == 1
    html = _read("index.html")
    assert "has-dock" not in html and "--sp-dock" not in html


def test_p8_dock_block_min_zero_no_transition_after_drawer_rules():
    """AC-5.3/5.4 (dock part): min-width/min-height 0 on the aside, --sp-dock only in the wide block, no grid transition."""
    css = _css()
    by = {sel: _norm(b) for _, sel, b in _dock_rules(css)}
    aside = by.get("#app.has-dock > .drawer", "")
    for want in ("min-width: 0", "min-height: 0", "position: relative", "grid-column: 2", "z-index: auto"):
        assert want in aside, want
    assert "minmax(0, 1fr)" in by.get("#app.has-dock", "")
    assert not re.search(r"transition[^;{}]*grid-template-columns", css)
    assert not re.search(r"@media[^{]*print[^{]*\{[^{}]*\{[^{}]*--sp-dock", css)
