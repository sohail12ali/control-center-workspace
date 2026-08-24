"""Vault plugin: read-only file tree/viewer and the wikilink graph."""

from .. import vault as vault_mod
from ..plugins.base import Plugin


def apply(ctx):
    repo_root = ctx.repo_root

    ctx.register_tab("vault", label="Vault", short="Graph", icon="graph", group="main", needs_live=True)

    def tree(req):
        return vault_mod.list_tree(repo_root, req.query.get("path", ""))

    def read(req):
        return vault_mod.read_file(repo_root, req.query.get("path", ""))

    def graph(req):
        return vault_mod.build_graph(repo_root)

    def search(req):
        return vault_mod.search(repo_root, req.query.get("q", ""))

    ctx.get(r"^/api/vault/tree/?$", tree, "vault.tree")
    ctx.get(r"^/api/vault/file/?$", read, "vault.file")
    ctx.get(r"^/api/vault/graph/?$", graph, "vault.graph")
    ctx.get(r"^/api/vault/search/?$", search, "vault.search")


PLUGIN = Plugin(
    id="vault",
    apply=apply,
    summary="knowledge-center link graph and read-only file reader.",
)
