"""Static snapshot export — a folder you can open from `file://`, or hand to
someone who will never run the server.

Two rules keep it honest:

1. **One rendering path.** Every payload here comes from the same view-model
   functions the live routes use (render.py, overview.py, todos_agg.py), so
   `serve` and `export` cannot drift into showing different numbers.

2. **One manifest.** The tab list is built by actually loading the plugin
   registry, not by re-listing tabs in this file. A plugin disabled in
   `config/plugins.toml` is therefore absent from an export for the same
   reason it is absent from the server, and adding a plugin needs no edit
   here.

`needs_live` tabs are dropped from the exported manifest. A tab earns that
flag when a frozen snapshot would misrepresent it — Agents launches
processes; Work and Analytics have date/window pickers; Vault's tree and file
reader are per-path. The frontend maps `/api/x/y?q=…` to `data/x-y.json`
(Console.staticFileFor), which discards the query string, so a parameterised
endpoint would serve one frozen answer to every different question. Hiding
those tabs is the honest option; the alternative is a UI whose filters
silently do nothing.
"""

import glob
import json
import os
import shutil

from . import boards as boards_mod, overview, render, todos_agg
from .paths import find_repo_root
from .plugins import build

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")

# Injected before any other script: Console.IS_STATIC is read while core.js
# is evaluating, and the data script must already be in place by the time the
# router boots. data.js (a plain <script>, not fetch) is what makes the export
# work from a file:// URL at all — Chromium gives such a page a null origin
# and refuses fetch() against it, so a JSON-fetching snapshot never boots.
_STATIC_HEAD = (
    "<script>window.__STATIC__ = true;</script>\n"
    '<script src="data.js"></script>\n'
)

# Payload builders for tabs that survive the needs_live filter. Keyed by tab
# id; a tab with no entry contributes no data file (About and Settings need
# none — they render from the manifest and localStorage).
_TAB_DATA = {
    "overview": ("overview", overview.full_overview),
    "todos": ("todos", todos_agg.all_todos),
}


def _dump(data_dir, name, payload):
    with open(os.path.join(data_dir, name), "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def _export_manifest(repo_root):
    """The live /api/config payload, minus the tabs a snapshot can't honour."""
    console_config = boards_mod.load_console_config(repo_root)
    ctx, _router = build(repo_root, console_config)

    # Same ordering rule the shell plugin serves, imported rather than copied.
    from .features.shell_feature import nav_sort_key

    tabs = ctx.tabs()
    ordered = [tabs[k] for k in sorted(tabs, key=nav_sort_key)]
    kept = [t for t in ordered if not t.get("needs_live")]
    dropped = [t["id"] for t in ordered if t.get("needs_live")]

    general = console_config.get("general", {})
    manifest = {
        "title": general.get("title", "Delivery Console"),
        "subtitle": general.get("subtitle", ""),
        "tabs": kept,
        "boards": [{"kind": t["kind"], "label": t["label"]} for t in kept if t.get("group") == "boards"],
        "stale_days": general.get("stale_days", 7),
        "static": True,
    }
    return manifest, kept, dropped


def _copy_frontend(out_dir):
    """Every asset, not a hand-listed subset: a tab added as one new .js file
    must not need this list edited to appear in an export."""
    copied = []
    for pattern in ("*.html", "*.js", "*.css"):
        for src in sorted(glob.glob(os.path.join(STATIC_DIR, pattern))):
            name = os.path.basename(src)
            shutil.copyfile(src, os.path.join(out_dir, name))
            copied.append(name)

    index_path = os.path.join(out_dir, "index.html")
    if os.path.isfile(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            html = f.read()
        if "__STATIC__" not in html:
            html = html.replace("</head>", _STATIC_HEAD + "</head>", 1)
            with open(index_path, "w", encoding="utf-8") as f:
                f.write(html)
    return copied


def export_static(repo_root=None, out_dir=None):
    repo_root = repo_root or find_repo_root()
    if not out_dir:
        raise ValueError("--out is required")
    os.makedirs(out_dir, exist_ok=True)
    data_dir = os.path.join(out_dir, "data")
    os.makedirs(data_dir, exist_ok=True)

    manifest, kept, dropped = _export_manifest(repo_root)

    # Keys match Console.staticKeyFor(): the API path minus /api/, query
    # dropped, slashes to dashes. One mapping, so a tab that works live works
    # in the export without knowing an export exists.
    payloads = {"config": manifest, "boards": render.boards_index(repo_root)}

    for entry in manifest["boards"]:
        view = render.board_view(entry["kind"], repo_root)
        payloads[f"board-{entry['kind']}"] = view
        # Card drawers read /api/ticket/{id}. Capturing them keeps the
        # snapshot's cards clickable instead of dead rectangles.
        for lane in view["lanes"]:
            for card in lane["cards"]:
                payloads[f"ticket-{card['id']}"] = render.ticket_view(card["id"], repo_root)
        for card in view["orphans"]:
            payloads[f"ticket-{card['id']}"] = render.ticket_view(card["id"], repo_root)

    for tab in kept:
        spec = _TAB_DATA.get(tab["id"])
        if spec:
            key, builder = spec
            payloads[key] = builder(repo_root)

    for key, payload in payloads.items():
        _dump(data_dir, f"{key}.json", payload)

    # The file the page actually reads. See _STATIC_HEAD.
    with open(os.path.join(out_dir, "data.js"), "w", encoding="utf-8") as f:
        f.write("/* Generated by console/server/export.py — do not edit. */\n")
        f.write("window.__CONSOLE_DATA__ = ")
        json.dump(payloads, f, indent=2)
        f.write(";\n")

    _copy_frontend(out_dir)

    with open(os.path.join(out_dir, "static-export.json"), "w", encoding="utf-8") as f:
        json.dump(
            {
                "static": True,
                "tabs": [t["id"] for t in kept],
                "omitted_needs_live": dropped,
                "boards": [b["kind"] for b in manifest["boards"]],
            },
            f,
            indent=2,
        )

    return out_dir
