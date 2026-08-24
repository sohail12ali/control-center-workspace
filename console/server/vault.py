"""Vault tab: a read-only folder tree + file viewer, and a wikilink graph
over knowledge-center/. Generic wikilink + folder-containment edges only —
drops the fork's typed frontmatter edge schema (fk_to/related_procedures/
calls), which was that project's own knowledge-graph vocabulary, not a
generic concept. A fork can still add typed edges later by extending
`_extract_wikilinks` without touching the graph/tree/file-read plumbing.
"""

import os
import re

VAULT_SUBDIR = "knowledge-center"
MAX_FILE_BYTES = 256 * 1024
_TEXT_EXTENSIONS = {".md", ".toml", ".txt", ".sql", ".yaml", ".yml", ".json"}
_WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)")


def _vault_root(repo_root):
    return os.path.join(repo_root, VAULT_SUBDIR)


def _safe_join(repo_root, rel_path):
    """Resolve rel_path under the vault root; raise if it escapes."""
    root = os.path.abspath(_vault_root(repo_root))
    target = os.path.abspath(os.path.join(root, rel_path or ""))
    if not (target == root or target.startswith(root + os.sep)):
        raise ValueError(f"path escapes vault root: {rel_path!r}")
    return target


def list_tree(repo_root, rel_path=""):
    """One level of the folder tree — lazy, not recursive, so a large vault
    doesn't require scanning everything just to render a tree view."""
    target = _safe_join(repo_root, rel_path)
    if not os.path.isdir(target):
        raise FileNotFoundError(f"not a directory: {rel_path!r}")
    entries = []
    for name in sorted(os.listdir(target)):
        if name.startswith("."):
            continue
        full = os.path.join(target, name)
        entry_rel = os.path.join(rel_path, name) if rel_path else name
        if os.path.isdir(full):
            entries.append({"name": name, "path": entry_rel.replace("\\", "/"), "type": "dir"})
        else:
            entries.append(
                {
                    "name": name,
                    "path": entry_rel.replace("\\", "/"),
                    "type": "file",
                    "size": os.path.getsize(full),
                }
            )
    return entries


def read_file(repo_root, rel_path):
    target = _safe_join(repo_root, rel_path)
    if not os.path.isfile(target):
        raise FileNotFoundError(f"not a file: {rel_path!r}")
    size = os.path.getsize(target)
    if size > MAX_FILE_BYTES:
        raise ValueError(f"file too large to view ({size} bytes, cap {MAX_FILE_BYTES})")
    try:
        with open(target, "r", encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        raise ValueError("binary or non-UTF-8 file, cannot preview") from None
    return {"path": rel_path, "size": size, "content": content}


def _extract_wikilinks(text):
    return [m.group(1).strip() for m in _WIKILINK_RE.finditer(text)]


def _walk_vault_files(repo_root):
    root = _vault_root(repo_root)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for name in filenames:
            if name.startswith("."):
                continue
            ext = os.path.splitext(name)[1].lower()
            if ext not in _TEXT_EXTENSIONS:
                continue
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root).replace("\\", "/")
            yield rel, full


def search(repo_root, query, limit=60):
    """Filename/path substring search across vault text files. Deliberately
    not a content grep — that's what the editor is for; this exists so the
    file tree is navigable without clicking down every folder."""
    query = (query or "").strip().lower()
    if not query:
        return []
    hits = []
    for rel, _full in _walk_vault_files(repo_root):
        if query in rel.lower():
            hits.append({"path": rel, "name": os.path.basename(rel)})
            if len(hits) >= limit:
                break
    return hits


def build_graph(repo_root, max_files=5000):
    """Nodes: one per text file under knowledge-center/ (id = relative
    path). Edges: 'wikilink' between resolved [[bare-name]] references
    (matched by basename without extension, since that's this template's
    convention), and 'contains' from every file to its parent folder node
    (so non-markdown files aren't orphaned)."""
    nodes = {}
    by_basename = {}
    files = list(_walk_vault_files(repo_root))[:max_files]

    for rel, full in files:
        basename = os.path.splitext(os.path.basename(rel))[0]
        nodes[rel] = {"id": rel, "label": os.path.basename(rel), "kind": os.path.splitext(rel)[1].lstrip(".")}
        by_basename.setdefault(basename, []).append(rel)

    edges = []
    seen_folders = set()
    for rel, full in files:
        folder = os.path.dirname(rel)
        if folder and folder not in seen_folders:
            seen_folders.add(folder)
            nodes.setdefault(folder, {"id": folder, "label": os.path.basename(folder) or folder, "kind": "folder"})
        if folder:
            edges.append({"source": rel, "target": folder, "type": "contains"})

        if os.path.splitext(rel)[1].lower() != ".md":
            continue
        try:
            with open(full, "r", encoding="utf-8") as f:
                text = f.read()
        except (UnicodeDecodeError, OSError):
            continue
        for link in _extract_wikilinks(text):
            targets = by_basename.get(link)
            if not targets:
                continue
            for target_rel in targets:
                if target_rel != rel:
                    edges.append({"source": rel, "target": target_rel, "type": "wikilink"})

    # Degree drives node size and the orphan filter, and the folder lets the
    # UI group/colour by area. Computed here rather than in the browser so the
    # static export carries the same numbers as the live server.
    degree = {}
    for e in edges:
        if e["type"] == "wikilink":
            degree[e["source"]] = degree.get(e["source"], 0) + 1
            degree[e["target"]] = degree.get(e["target"], 0) + 1
    for nid, node in nodes.items():
        node["links"] = degree.get(nid, 0)
        node["folder"] = os.path.dirname(nid) or ""
        node["md"] = node["kind"] == "md"

    return {
        "nodes": list(nodes.values()),
        "edges": edges,
        "truncated": len(files) >= max_files,
        "folders": sorted({n["folder"] for n in nodes.values() if n["folder"]}),
    }
