#!/usr/bin/env python3
"""
Smoke-test ``definitions/components.json`` for shape regressions.

Loads the catalog via ``ComponentCatalog`` (i.e. through the same
JSON loader the API uses), then asserts that a curated list of
well-known components are present and structured the way the
frontend expects. Catches:

- A new ``ComponentCategory`` value the loader doesn't know about
- A popular component disappearing from the catalog
- A field's type changing in a way that would break form rendering
  (e.g. ``output.gpio.pin`` flipping from ``pin`` to ``string``)
- ``id`` fields regressing into spurious cross-references

Designed to run in CI right after ``script/sync_components.py``,
before the diff-budget check / PR creation. Exits non-zero on the
first violation with a clear "[component].[field] expected X, got Y"
message so the operator can read the workflow log without spelunking.

Run locally:

    python script/check_catalog.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running via ``python script/check_catalog.py`` without
# installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from esphome_device_builder.controllers.components import ComponentCatalog

# Per-component shape assertions. Each entry is a tuple of
# ``(component_id, [(field_key, type, required, refs)])``. A field
# is a 4-tuple where ``type`` is a ConfigEntryType.value, ``required``
# is bool or None (don't care), and ``refs`` is the expected
# ``references_component`` value or None (don't care).
#
# The list is intentionally short — these are the components the
# frontend uses on every device's "Add component" flow. If they
# break, the whole catalog UX breaks.
_EXPECTATIONS: list[tuple[str, list[tuple[str, str, bool | None, str | None]]]] = [
    (
        "wifi",
        [
            ("ssid", "string", None, None),
            ("password", "secure_string", None, None),
        ],
    ),
    (
        "api",
        [
            ("encryption", "nested", None, None),
        ],
    ),
    (
        "esphome",
        [
            ("name", "string", True, None),
            ("comment", "string", None, None),
            ("areas", "nested", None, None),
        ],
    ),
    (
        "logger",
        [
            ("level", "string", None, None),
            ("logs", "map", None, None),
        ],
    ),
    (
        "i2c",
        [
            ("sda", "pin", None, None),
            ("scl", "pin", None, None),
        ],
    ),
    (
        "esp32",
        [
            ("variant", "string", None, None),
            ("framework", "nested", None, None),
        ],
    ),
    (
        "ota.esphome",
        [
            ("password", "secure_string", None, None),
        ],
    ),
    (
        "sensor.dht",
        [
            ("pin", "pin", True, None),
            ("temperature", "nested", None, None),
            ("humidity", "nested", None, None),
        ],
    ),
    (
        "output.gpio",
        [
            ("pin", "pin", True, None),
            # The classic regression: id used to be type=string with
            # references_component="gpio". It's the component's OWN id.
            ("id", "id", True, None),
            # power_supply IS a real cross-reference and must stay
            # one — guards the inverse regression.
            ("power_supply", "id", None, "power_supply"),
        ],
    ),
    (
        "light.binary",
        [
            ("output", "id", True, "output"),
        ],
    ),
    (
        "switch.gpio",
        [
            ("pin", "pin", True, None),
        ],
    ),
]


def main() -> int:
    catalog = ComponentCatalog()
    catalog.load()
    if not catalog._components:
        print("ERROR: catalog is empty — sync_components.py probably failed.")
        return 2

    failures: list[str] = []
    for component_id, fields in _EXPECTATIONS:
        component = catalog._by_id.get(component_id)
        if component is None:
            failures.append(f"missing component: {component_id}")
            continue
        for key, expected_type, expected_required, expected_refs in fields:
            entry = next((e for e in component.config_entries if e.key == key), None)
            if entry is None:
                failures.append(f"{component_id}: missing field {key!r}")
                continue
            actual_type = str(entry.type)
            if actual_type != expected_type:
                failures.append(
                    f"{component_id}.{key}: type expected {expected_type!r}, got {actual_type!r}"
                )
            if expected_required is not None and entry.required != expected_required:
                failures.append(
                    f"{component_id}.{key}: required expected {expected_required}, "
                    f"got {entry.required}"
                )
            if entry.references_component != expected_refs:
                failures.append(
                    f"{component_id}.{key}: references_component expected "
                    f"{expected_refs!r}, got {entry.references_component!r}"
                )

    if failures:
        print(f"FAIL: {len(failures)} catalog regression(s):")
        for line in failures:
            print(f"  - {line}")
        return 1

    field_count = sum(len(fields) for _, fields in _EXPECTATIONS)
    print(f"OK: {len(_EXPECTATIONS)} components, {field_count} fields verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
