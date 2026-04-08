# API Reference

Base URL: `http://localhost:6052`

## WebSocket API (`/ws`)

The primary API. A single multiplexed WebSocket handles all commands.

### Protocol

**Connect:** `ws://localhost:6052/ws`

On connect, the server sends:
```json
{"server_version": "0.0.0", "esphome_version": "2026.3.1"}
```

**Send a command:**
```json
{"command": "devices/list", "message_id": "1", "args": {}}
```

**Receive a result:**
```json
{"message_id": "1", "result": { ... }}
```

**Streaming output (compile/upload/logs):**
```json
{"message_id": "1", "event": "output", "data": "Compiling...\n"}
{"message_id": "1", "event": "result", "data": {"success": true, "code": 0}}
```

**Error:**
```json
{"message_id": "1", "error_code": "unknown_command", "details": "..."}
```

### Error Codes

| Code | Description |
|------|-------------|
| `invalid_message` | Malformed JSON or missing fields |
| `unknown_command` | Command not found |
| `invalid_args` | Missing or invalid arguments |
| `not_found` | Resource not found |
| `internal_error` | Server error |

---

## Commands

### Devices

| Command | Args | Response | Description |
|---------|------|----------|-------------|
| `devices/list` | — | `DevicesResponse` | List configured + importable devices |
| `devices/get_states` | — | `dict` | Get device online/offline states |
| `devices/create` | `{name, config_type?, platform?, board?, ssid?, psk?, password?, file_content?, board_id?}` | `WizardResponse` | Create new device config |
| `devices/update` | `{name, friendly_name?, comment?, board_id?}` | `UpdateDeviceResponse` | Update device metadata |
| `devices/delete` | `{configuration}` | — | Delete device and associated files |
| `devices/get_config` | `{configuration}` | `string` | Read device YAML config |
| `devices/update_config` | `{configuration, content}` | — | Write device YAML config |
| `devices/add_component` | `{configuration, component_id, fields?, sub_entities?}` | `AddComponentResponse` | Add component to device config |
| `devices/import` | `{name, project_name?, package_import_url?, friendly_name?, encryption?}` | `dict` | Import/adopt discovered device |
| `devices/ignore` | `{name, ignore?}` | — | Toggle device visibility in import list |
| `devices/compile` | `{configuration}` | Streaming | Compile device firmware |
| `devices/upload` | `{configuration, port?}` | Streaming | Upload firmware to device |
| `devices/logs` | `{configuration, port?}` | Streaming | Stream device logs |
| `devices/validate` | `{configuration}` | Streaming | Validate YAML config |
| `devices/clean` | `{configuration}` | Streaming | Clean build files |

### Boards

| Command | Args | Response | Description |
|---------|------|----------|-------------|
| `boards/get_boards` | `{query?, platform?, variant?, tag?, offset?, limit?}` | `PagedBoardsResponse` | Search/list boards |
| `boards/get_board` | `{board_id}` | `BoardCatalogEntry` | Get single board with pin map |

### Components

| Command | Args | Response | Description |
|---------|------|----------|-------------|
| `components/get_components` | `{query?, category?, offset?, limit?}` | `PagedComponentsResponse` | Search/list components |
| `components/get_component` | `{component_id}` | `ComponentCatalogEntry` | Get component with config entries |

### Config

| Command | Args | Response | Description |
|---------|------|----------|-------------|
| `config/version` | — | `{server_version, esphome_version}` | Get versions |
| `config/serial_ports` | — | `[{port, desc}]` | List serial ports |
| `config/get_preferences` | — | `dict` | Get user preferences |
| `config/set_preferences` | `{...prefs}` | `dict` | Update user preferences |
| `config/get_secrets` | — | `[string]` | List secret key names |
| `config/get_info` | `{configuration}` | `dict` | Get compiled device metadata |

### Utility

| Command | Args | Response | Description |
|---------|------|----------|-------------|
| `ping` | — | `{pong: true}` | Health check |
| `subscribe_events` | — | Streaming events | Subscribe to state changes |

---

## Legacy REST Endpoints (Deprecated)

For backward compatibility with the Home Assistant ESPHome integration only.
New clients must use the `/ws` WebSocket API.

| Endpoint | Description |
|----------|-------------|
| `GET /devices` | List devices (HA dashboard-api) |
| `GET /json-config?configuration=...` | Get parsed YAML as JSON |
| `GET /compile` (WebSocket) | Compile via spawn protocol |
| `GET /upload` (WebSocket) | Upload via spawn protocol |
