"""Backend SPI — the ticket-storage abstraction. See base.py for the contract,
vault_backend.py for the (sole, T-017 BR-4) adapter."""

from .base import Backend, BackendError
from .vault_backend import VaultBackend
from .vault_backend import default as default_backend

__all__ = ["Backend", "BackendError", "VaultBackend", "default_backend"]
