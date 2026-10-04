"""Backend SPI interface (T-017 FR-5, decision-log a4).

Phase 1 (1b): the interface only — enforced by `abc.ABC`, so an incomplete
implementation cannot be instantiated at all. The one real adapter
(`VaultBackend`) lands in Phase 2's 2b and is not exercised here.
"""

import pytest

from server import backends
from server.backends.base import Backend


ALL_METHODS = ("list", "show", "create", "move", "set", "comment", "ready", "claim")


class _Complete(Backend):
    def list(self, repo_root, kind=None, stage=None, owner=None):
        return []

    def show(self, repo_root, ticket_id):
        return None

    def create(self, repo_root, ticket_id, title, **fields):
        return {}

    def move(self, repo_root, ticket_id, stage):
        return {}

    def set(self, repo_root, ticket_id, field, value):
        return {}

    def comment(self, repo_root, ticket_id, text, **fields):
        return {}

    def ready(self, repo_root, **filters):
        return []

    def claim(self, repo_root, ticket_id, claimed_by):
        return {}


class TestInterfaceContract:
    def test_the_public_shape_is_exported(self):
        assert backends.Backend is Backend
        assert issubclass(backends.BackendError, ValueError)

    def test_a_complete_implementation_instantiates(self):
        assert isinstance(_Complete(), Backend)

    @pytest.mark.parametrize("missing", ALL_METHODS)
    def test_missing_any_one_method_refuses_to_instantiate(self, missing):
        namespace = {
            name: (lambda self, *a, **kw: None)
            for name in ALL_METHODS if name != missing
        }
        Incomplete = type("Incomplete", (Backend,), namespace)
        with pytest.raises(TypeError):
            Incomplete()

    def test_bare_backend_cannot_be_instantiated(self):
        with pytest.raises(TypeError):
            Backend()
