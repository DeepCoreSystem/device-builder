"""Multiplexed WebSocket API handler.

Single /ws endpoint with command/response protocol and message_id correlation.
Supports request-response and streaming (compile, upload, logs).
"""

from __future__ import annotations

import asyncio
import logging
import sys
from collections.abc import Callable, Coroutine
from typing import Any

import orjson
from aiohttp import WSMsgType, web

from ..const import __version__
from ..dashboard import DASHBOARD, DashboardEvent
from ..models import (
    CommandMessage,
    ErrorCode,
    ErrorMessage,
    EventMessage,
    ResultMessage,
    ServerInfoMessage,
)

_LOGGER = logging.getLogger(__name__)

routes = web.RouteTableDef()

# Type for command handlers
CommandHandler = Callable[..., Coroutine[Any, Any, Any]]

# Registry of command handlers
_COMMAND_HANDLERS: dict[str, CommandHandler] = {}


def api_command(command: str) -> Callable[[CommandHandler], CommandHandler]:
    """Register a function as a WebSocket API command handler."""

    def decorator(func: CommandHandler) -> CommandHandler:
        _COMMAND_HANDLERS[command] = func
        return func

    return decorator


# ---------------------------------------------------------------------------
# WebSocket connection
# ---------------------------------------------------------------------------


class WebSocketClient:
    """A single WebSocket client connection."""

    def __init__(self, ws: web.WebSocketResponse, app: web.Application) -> None:
        self._ws = ws
        self._app = app
        self._tasks: set[asyncio.Task] = set()

    async def send(self, data: dict[str, Any]) -> None:
        """Send a JSON message to the client."""
        try:
            await self._ws.send_bytes(orjson.dumps(data))
        except ConnectionResetError:
            pass

    async def send_result(self, message_id: str, result: Any = None) -> None:
        """Send a success result."""
        msg = ResultMessage(message_id=message_id, result=result)
        await self.send(msg.to_dict())

    async def send_error(self, message_id: str, error_code: ErrorCode, details: str = "") -> None:
        """Send an error result."""
        msg = ErrorMessage(message_id=message_id, error_code=error_code, details=details)
        await self.send(msg.to_dict())

    async def send_event(self, message_id: str, event: str, data: Any = None) -> None:
        """Send a streaming event."""
        msg = EventMessage(message_id=message_id, event=event, data=data)
        await self.send(msg.to_dict())

    async def _handle_command(self, raw: dict[str, Any]) -> None:
        """Parse and dispatch a command."""
        try:
            cmd = CommandMessage.from_dict(raw)
        except Exception:
            await self.send_error("", ErrorCode.INVALID_MESSAGE, "Invalid command format")
            return

        handler = _COMMAND_HANDLERS.get(cmd.command)
        if handler is None:
            await self.send_error(
                cmd.message_id, ErrorCode.UNKNOWN_COMMAND, f"Unknown command: {cmd.command}"
            )
            return

        try:
            result = await handler(self, cmd.message_id, cmd.args)
            # If the handler returns something, send it as a result
            # (streaming handlers send their own messages and return None)
            if result is not None:
                await self.send_result(cmd.message_id, result)
        except Exception:
            _LOGGER.exception("Error handling command %s", cmd.command)
            await self.send_error(
                cmd.message_id, ErrorCode.INTERNAL_ERROR, f"Command failed: {cmd.command}"
            )

    def _create_task(self, coro: Coroutine) -> asyncio.Task:
        """Create a tracked task."""
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    async def cleanup(self) -> None:
        """Cancel all pending tasks."""
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

_ESPHOME_CMD = [sys.executable, "-m", "esphome"]


async def _stream_esphome_command(
    client: WebSocketClient,
    message_id: str,
    command: str,
    config_path: str,
    extra_args: list[str] | None = None,
) -> None:
    """Run an esphome CLI command and stream output."""
    cmd = [*_ESPHOME_CMD, command, config_path]
    if extra_args:
        cmd.extend(extra_args)

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
    except Exception as exc:
        await client.send_error(message_id, ErrorCode.INTERNAL_ERROR, str(exc))
        return

    assert proc.stdout is not None
    async for line_bytes in proc.stdout:
        line = line_bytes.decode("utf-8", errors="replace")
        await client.send_event(message_id, "output", line)

    exit_code = await proc.wait()
    await client.send_event(message_id, "result", {"success": exit_code == 0, "code": exit_code})


@api_command("compile")
async def cmd_compile(client: WebSocketClient, message_id: str, args: dict[str, Any]) -> None:
    """Compile a device configuration."""
    configuration = args.get("configuration", "")
    if not configuration:
        await client.send_error(message_id, ErrorCode.INVALID_ARGS, "configuration is required")
        return
    settings = client._app["settings"]
    config_path = str(settings.rel_path(configuration))
    await _stream_esphome_command(client, message_id, "compile", config_path)


@api_command("upload")
async def cmd_upload(client: WebSocketClient, message_id: str, args: dict[str, Any]) -> None:
    """Upload firmware to a device."""
    configuration = args.get("configuration", "")
    port = args.get("port", "")
    if not configuration:
        await client.send_error(message_id, ErrorCode.INVALID_ARGS, "configuration is required")
        return
    settings = client._app["settings"]
    config_path = str(settings.rel_path(configuration))
    extra = ["--device", port] if port else []
    await _stream_esphome_command(client, message_id, "upload", config_path, extra)


@api_command("logs")
async def cmd_logs(client: WebSocketClient, message_id: str, args: dict[str, Any]) -> None:
    """Stream device logs."""
    configuration = args.get("configuration", "")
    port = args.get("port", "")
    if not configuration:
        await client.send_error(message_id, ErrorCode.INVALID_ARGS, "configuration is required")
        return
    settings = client._app["settings"]
    config_path = str(settings.rel_path(configuration))
    extra = ["--device", port] if port else []
    await _stream_esphome_command(client, message_id, "logs", config_path, extra)


@api_command("validate")
async def cmd_validate(client: WebSocketClient, message_id: str, args: dict[str, Any]) -> None:
    """Validate a device configuration."""
    configuration = args.get("configuration", "")
    if not configuration:
        await client.send_error(message_id, ErrorCode.INVALID_ARGS, "configuration is required")
        return
    settings = client._app["settings"]
    config_path = str(settings.rel_path(configuration))
    await _stream_esphome_command(client, message_id, "config", config_path)


@api_command("clean")
async def cmd_clean(client: WebSocketClient, message_id: str, args: dict[str, Any]) -> None:
    """Clean build files."""
    configuration = args.get("configuration", "")
    if not configuration:
        await client.send_error(message_id, ErrorCode.INVALID_ARGS, "configuration is required")
        return
    settings = client._app["settings"]
    config_path = str(settings.rel_path(configuration))
    await _stream_esphome_command(client, message_id, "clean", config_path)


@api_command("ping")
async def cmd_ping(client: WebSocketClient, message_id: str, args: dict[str, Any]) -> dict:
    """Respond to ping with pong."""
    return {"pong": True}


@api_command("subscribe_events")
async def cmd_subscribe_events(
    client: WebSocketClient, message_id: str, args: dict[str, Any]
) -> None:
    """Subscribe to dashboard state events."""

    def _on_event(event_type: DashboardEvent, data: Any) -> None:
        """Forward dashboard events to the client."""
        task = asyncio.create_task(client.send_event(message_id, event_type.value, data))
        _ = task  # prevent GC

    DASHBOARD.bus.subscribe(_on_event)

    # Send initial state
    entries = await DASHBOARD.entries.async_all()
    await client.send_event(
        message_id,
        "initial_state",
        {
            "devices": [
                {
                    "name": entry.name,
                    "configuration": entry.filename,
                    "friendly_name": entry.friendly_name,
                }
                for entry in entries
            ],
        },
    )

    # The subscription stays active for the lifetime of the connection
    # Result is sent immediately to confirm subscription
    await client.send_result(message_id, {"subscribed": True})


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------


@routes.get("/ws")
async def websocket_handler(request: web.Request) -> web.WebSocketResponse:
    """Multiplexed WebSocket API endpoint."""
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    client = WebSocketClient(ws, request.app)

    # Send server info on connect
    try:
        from esphome.const import __version__ as esphome_version
    except ImportError:
        esphome_version = "unknown"

    info = ServerInfoMessage(
        server_version=__version__,
        esphome_version=esphome_version,
    )
    await client.send(info.to_dict())

    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                try:
                    raw = orjson.loads(msg.data)
                except Exception:
                    await client.send_error("", ErrorCode.INVALID_MESSAGE, "Invalid JSON")
                    continue
                # Dispatch command in a task so multiple commands can run concurrently
                client._create_task(client._handle_command(raw))
            elif msg.type == WSMsgType.BINARY:
                try:
                    raw = orjson.loads(msg.data)
                except Exception:
                    _LOGGER.debug("Invalid binary message received")
                    continue
                client._create_task(client._handle_command(raw))
            elif msg.type in (WSMsgType.ERROR, WSMsgType.CLOSE):
                break
    finally:
        await client.cleanup()
        _LOGGER.debug("WebSocket client disconnected")

    return ws
