"""Minimal smoke tests so CI's pytest job has at least one collectable test.

These intentionally don't exercise behaviour — that's what
``script/check_catalog.py`` and ``script/validate_definitions.py``
are for. The goal here is to verify that the package imports
cleanly across the supported Python versions in our matrix, since
import-time errors (typing constructs, conditional imports, missing
deps) are the most common breakage when bumping Python.

Real tests should live alongside this file as ``tests/test_<area>.py``
and use ``pytest_asyncio_mode = "auto"`` (already set in
``pyproject.toml``) for async cases.
"""

from __future__ import annotations


def test_package_imports() -> None:
    """Top-level package imports without side effects."""
    import esphome_device_builder  # noqa: F401


def test_controllers_import() -> None:
    """Each controller module is importable on its own."""
    # Import lazily so a failure in one controller doesn't poison
    # diagnosis of the others.
    from esphome_device_builder.controllers import (  # noqa: F401
        automations,
        boards,
        components,
        config,
        devices,
        editor,
        firmware,
    )


def test_models_import() -> None:
    """Public model surface is importable."""
    from esphome_device_builder.models import (  # noqa: F401
        ComponentCatalogEntry,
        ConfigEntry,
        ConfigEntryType,
        EventType,
        FirmwareJob,
        JobStatus,
        JobType,
    )
