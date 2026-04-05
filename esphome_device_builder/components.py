"""Backward-compat shim — use controllers.components instead."""

from .controllers.components import COMPONENT_CATALOG, ComponentCatalog

__all__ = ["COMPONENT_CATALOG", "ComponentCatalog"]
