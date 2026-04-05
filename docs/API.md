# API Reference

Base URL: `http://localhost:6052`

## WebSocket API (`/ws`)

The primary API for the frontend. A single multiplexed WebSocket connection handles all commands.

### Protocol

**Connect:** `ws://localhost:6052/ws`

On connect, the server sends a `ServerInfoMessage`:
```json
{"server_version": "0.0.0", "esphome_version": "2026.3.1"}
```

**Send a command:**
```json
{"command": "compile", "message_id": "1", "args": {"configuration": "device.yaml"}}
```

**Receive a result (single response):**
```json
{"message_id": "1", "result": {"pong": true}}
```

**Receive streaming output (compile/upload/logs):**
```json
{"message_id": "1", "event": "output", "data": "Compiling...\n"}
{"message_id": "1", "event": "output", "data": "Done.\n"}
{"message_id": "1", "event": "result", "data": {"success": true, "code": 0}}
```

**Error:**
```json
{"message_id": "1", "error_code": "unknown_command", "details": "Unknown command: foo"}
```

### Commands

| Command | Args | Response | Description |
|---------|------|----------|-------------|
| `compile` | `{configuration}` | Streaming output + result | Compile device firmware |
| `upload` | `{configuration, port?}` | Streaming output + result | Upload firmware to device |
| `logs` | `{configuration, port?}` | Streaming output | Stream device logs |
| `validate` | `{configuration}` | Streaming output + result | Validate YAML config |
| `clean` | `{configuration}` | Streaming output + result | Clean build files |
| `ping` | — | `{pong: true}` | Health check |
| `subscribe_events` | — | Streaming events | Subscribe to device state changes |

### Error Codes

| Code | Description |
|------|-------------|
| `invalid_message` | Malformed JSON or missing required fields |
| `unknown_command` | Command not found |
| `invalid_args` | Missing or invalid arguments |
| `not_found` | Resource not found |
| `internal_error` | Server error |

---

## REST API

All REST responses are JSON.

## Boards

### `GET /boards`

List boards with search, filtering, and pagination.

**Query parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | string | — | Free-text search (name, description, manufacturer, tags) |
| `platform` | string | — | Filter by platform (`esp32`, `esp8266`, `rp2040`, …) |
| `variant` | string | — | Filter by ESP32 variant (`esp32`, `esp32s3`, `esp32c3`, …) |
| `tag` | string | — | Filter by tag |
| `offset` | int | 0 | Pagination offset |
| `limit` | int | 50 | Page size (max 200) |

**Response:**

```json
{
  "boards": [ { "id": "...", "name": "...", ... } ],
  "total": 123,
  "offset": 0,
  "limit": 50
}
```

### `GET /boards/{board_id}`

Get a single board definition by ID, including pin map.

## Devices

### `GET /devices`

List all configured and importable (adoptable) devices.

### `GET /ping`

Get online/offline state for all devices.

### `POST /wizard`

Create a new device configuration.

**Body:** `{ "name", "ssid", "psk", "type": "basic"|"upload"|"empty", "platform", "board", "board_id" }`

### `PUT /devices/{name}`

Update device metadata (friendly_name, comment, board_id).

### `GET /edit?configuration=NAME.yaml`

Read a device config file.

### `POST /edit?configuration=NAME.yaml`

Write a device config file. **Body:** raw YAML text.

### `POST /delete?configuration=NAME.yaml`

Delete a device and its associated files.

### `POST /import`

Import/adopt a discovered device.

**Body:** `{ "name", "project_name", "package_import_url", "friendly_name", "encryption" }`

### `POST /ignore-device`

Toggle device visibility in the import list.

**Body:** `{ "name", "ignore": true|false }`

## Configuration Editing

### `GET /devices/{config}/section-config?key=SECTION`

Get editable config entries for a YAML section (e.g. `wifi`, `logger`, `api`).

### `POST /devices/{config}/section-config`

Update values in a YAML section.

### `POST /devices/{config}/components`

Add a component to a device config.

**Body:** `{ "component", "platform", "fields": { ... } }`

### `POST /devices/{config}/automations`

Add an automation to a device config.

**Body:** `{ "target_component_name", "trigger", "actions": [ ... ] }`

### `POST /devices/{config}/config-sections`

Add a config section (wifi, api, ota, etc.) to a device config.

**Body:** `{ "section", "fields": { ... } }`

## Catalogs

### `GET /components/catalog`

List all available component types with their platforms and fields.

### `GET /automations/catalog`

List all automation triggers and actions.

### `GET /config/catalog`

List all config section templates (wifi, api, ota, logger, …).

## Legacy WebSocket Endpoints (Deprecated)

These endpoints exist for backward compatibility with the Home Assistant ESPHome
integration (via `esphome-dashboard-api`). New clients should use `/ws` instead.

### `GET /compile`, `/upload` (WebSocket)

Used by HA for firmware compilation and OTA uploads.
Protocol: `{"type": "spawn", ...}` → `{"event": "line", ...}` → `{"event": "exit", "code": N}`

### `GET /logs`, `/validate`, `/clean`, `/rename` (WebSocket)

Same spawn-based protocol. Not used by HA — frontend-only.

### `GET /events` (WebSocket)

Legacy event subscription. Use `subscribe_events` command on `/ws` instead.

## Utilities

### `GET /version`

ESPHome version. Response: `{ "version": "2024.x.x" }`

### `GET /serial-ports`

List available serial ports.

### `GET /secret_keys`

List keys from `secrets.yaml`.

### `GET /preferences`

Get user preferences.

### `PUT /preferences`

Save user preferences. **Body:** `{ "editor_layout": "both"|"left"|"right" }`

### `GET /info?configuration=NAME.yaml`

Get compiled device metadata (address, versions, integrations).

### `GET /json-config?configuration=NAME.yaml`

Get parsed YAML config as JSON.

### `GET /downloads?configuration=NAME.yaml`

List available firmware binaries for download.

### `GET /download.bin?configuration=NAME.yaml&file=TYPE`

Download a compiled firmware binary.
