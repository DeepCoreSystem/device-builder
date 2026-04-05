"""Backward-compat shim — use controllers.boards instead."""

from .controllers.boards import BOARD_CATALOG, BoardCatalog

__all__ = ["BOARD_CATALOG", "BoardCatalog"]
