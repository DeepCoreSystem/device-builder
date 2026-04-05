"""Backward-compat shim — use controllers.metadata instead."""

from .controllers.metadata import (
    get_board_id,
    get_device_metadata,
    get_preferences,
    remove_device_metadata,
    set_device_metadata,
    set_preferences,
)

__all__ = [
    "get_board_id",
    "get_device_metadata",
    "get_preferences",
    "remove_device_metadata",
    "set_device_metadata",
    "set_preferences",
]
