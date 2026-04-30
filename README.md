# ESPHome Device Builder — Backend

> **Status: In Development**
> This project is under active development and aimed to replace the [current ESPHome dashboard](https://github.com/esphome/dashboard). Current stage is pretty much alpha (but close to beta/preview). Feel free to give it a test and report any found issues in the issue tracker (but please first check if there is an existing one reported). Goal is to have this new dashboard soon available as a preview (optional toggle to enable it) within the ESPHome container / HA App.

## What is this?

A new dashboard for [ESPHome](https://github.com/esphome/esphome) that provides a guided interface for composing device configurations. Users can explore devices, add components and boards step-by-step, manage automations, and push firmware updates.

This repository contains the **backend API server**. The frontend is a separate project: [esphome/device-builder-dashboard-frontend](https://github.com/esphome/device-builder-dashboard-frontend) but a prebuilt version is included into the release versions of this project.

## Try it

The dashboard isn't yet wired into the ESPHome container or the Home Assistant
add-on as an opt-in preview — that's coming soon. In the meantime there are two
ways to run a release locally:

### Option A — install a prebuilt wheel from a GitHub release

Each [release](https://github.com/esphome/device-builder-dashboard-backend/releases)
ships an `.whl` artifact you can `pip install` straight into a fresh venv. Pre-releases
(beta builds tagged like `2026.5.0b1`) are listed alongside the stable ones.

```bash
python -m venv .venv && source .venv/bin/activate

# Stable: copy the wheel URL from the latest release page
pip install https://github.com/esphome/device-builder-dashboard-backend/releases/download/<TAG>/esphome_device_builder-<TAG>-py3-none-any.whl

# Run it (point at any directory; it will be created on first use)
esphome-device-builder ~/esphome-configs
```

Once PyPI publishing is enabled (see CI section below), you'll also be able to
`pip install --pre esphome-device-builder` directly.

### Option B — run from source

See the **Development** section for the full setup.

### Coming soon

A beta toggle in the official ESPHome container and the Home Assistant
ESPHome add-on will install and launch this dashboard automatically — no
manual venv or wheel handling required.

## Development

### Setup

Requires [uv](https://docs.astral.sh/uv/):

```bash
git clone https://github.com/esphome/device-builder-dashboard-backend
cd device-builder-dashboard-backend
script/setup
```

### Running

```bash
source .venv/bin/activate
esphome-device-builder ./configs --log-level debug
```

The server starts on `http://localhost:6052`. Use the VS Code debugger (F5 → "Run Server") for breakpoint debugging.

### CLI Options

```
esphome-device-builder [configuration] [options]

  configuration      Path to ESPHome config directory (default: ./configs)
  --port PORT        HTTP port (default: 6052)
  --host HOST        Bind address (default: 0.0.0.0)
  --username USER    Dashboard username
  --password PASS    Dashboard password
  --ha-addon         Running as Home Assistant add-on
  --log-level LEVEL  Log level: debug, info (default), warning, error
  --log-file PATH    Log to rotating file
```

## Architecture

**WebSocket-first API** on `/ws` — 40+ commands, all through a single multiplexed WebSocket with command/response protocol (for a full reference, see docs/API.md).

```
DeviceBuilder (singleton)
├── controllers/devices.py       — device CRUD, validation, live logs
├── controllers/firmware.py      — job queue, compile, install, download
├── controllers/boards.py        —  handles board definitions (which include pin maps)
├── controllers/components.py    —  components registry from ESPHome
├── controllers/automations.py   —  context-aware triggers + actions
├── controllers/config.py        —  version, preferences, secrets
├── api/ws.py                    — /ws WebSocket dispatch
└── api/legacy.py                — HA backward compatibility endpoints
```

### Key concepts

- **A device** = a YAML config file on disk. Has `state` (online/offline/unknown via mDNS + ping), `has_pending_changes` (config changed since compile), and `update_available` (ESPHome version mismatch)
- **Device discovery** = mDNS browser for instant online/offline detection, ping sweep every 60s as fallback
- **Board definitions** = YAML manifests in `definitions/boards/`, specifically defined boatrds as well as generic fallbacks across 7 platforms (esp32, esp8266, rp2040, bk72xx, rtl87xx, ln882x, nrf52) with pin maps, hardware specs, images
- **Component catalog** = `definitions/components.json`, synced from ESPHome's pre-built schema bundle (with narrow live introspection for `multi_conf` / `platform_defaults` / `supported_platforms` and per-field MDX descriptions). 800+ components with config entries. Refreshed nightly by `.github/workflows/sync-component-catalog.yml`
- **Firmware jobs** = persistent queue, one at a time. Compile/install/upload. Survive page refresh and server restart
- **Real-time events** = subscribe once, get instant updates. No polling

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full architecture and [docs/API.md](docs/API.md) for the complete API reference with all 43 commands.

### Scripts

The board catalog is a curated set of popular boards with rich metadata.
To add a new board, create a subfolder under `esphome_device_builder/definitions/boards/`
with a `manifest.yaml`. See [definitions/README.md](esphome_device_builder/definitions/README.md).

```bash
python script/sync_components.py                    # Sync components against the latest ESPHome schema release
python script/sync_components.py --version 2026.4.3 # ...or pin to a specific schema version
python script/validate_definitions.py               # Validate all manifests
```

The same sync runs in CI nightly (and on manual dispatch with an
optional `version` input) — see
[`.github/workflows/sync-component-catalog.yml`](.github/workflows/sync-component-catalog.yml).
When the rebuild produces a diff it opens a PR against `main` for
human review.

## Board Definitions

Boards live in `esphome_device_builder/definitions/boards/`. Each board is a subfolder with a `manifest.yaml` and optional images. See [definitions/README.md](esphome_device_builder/definitions/README.md) for the schema and contributor guide.
It is intended to move this board definitions into a dedicated repository later as this project matures.

## Contributing

Contributions welcome — especially board definitions (add a subfolder to `definitions/boards/`).

Every PR needs **exactly one** of the following labels so it lands in the
right release-notes section: `breaking-change`, `new-feature`, `enhancement`,
`bugfix`, `refactor`, `docs`, `maintenance`, `ci`, `dependencies`. CI enforces
this via [`.github/workflows/pr-labels.yaml`](.github/workflows/pr-labels.yaml).

## Releasing (maintainer)

A rolling draft release is maintained automatically — every merge to `main`
appends a line under the matching label section, courtesy of
[release-drafter](.github/workflows/release-drafter.yml).

To ship a build:

1. Open the [Releases page](https://github.com/esphome/device-builder-dashboard-backend/releases),
   pick the existing draft, and edit it.
2. Set the tag:
   - **Stable** — `2026.5.0` (no `b` suffix). Leave "Set as a pre-release"
     unchecked.
   - **Beta** — `2026.5.0b1`. **Tick** "Set as a pre-release".
3. Hit **Publish**.

The [release workflow](.github/workflows/release.yml) then:
- validates the tag matches the prerelease checkbox (fails fast if they
  disagree),
- stamps `pyproject.toml` with the tag,
- builds the sdist + wheel,
- attaches both to the GitHub release,
- and publishes to PyPI when a `PYPI_TOKEN` repo secret is configured (no-op
  otherwise — the wheel attached to the release is the install path until
  PyPI is wired up).

## License

Apache-2.0 — Maintained by [Open Home Foundation](https://www.openhomefoundation.io/).
