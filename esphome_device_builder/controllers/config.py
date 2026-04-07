"""Config controller — settings, preferences, secrets, version, serial ports."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from esphome import yaml_util
from esphome.const import __version__ as esphome_version
from esphome.storage_json import StorageJSON, ext_storage_path
from esphome.util import get_serial_ports

from ..const import __version__ as server_version
from ..helpers.api import api_command
from .metadata import get_preferences, set_preferences

if TYPE_CHECKING:
    from ..device_builder import DeviceBuilder

_LOGGER = logging.getLogger(__name__)


class ConfigController:
    """Manages application configuration, preferences, and system info."""

    def __init__(self, device_builder: DeviceBuilder) -> None:
        self._db = device_builder

    @api_command("config/version")
    async def get_version(self, **kwargs: Any) -> dict:
        """Get ESPHome and server version."""
        return {"server_version": server_version, "esphome_version": esphome_version}

    @api_command("config/serial_ports")
    async def get_serial_ports(self, **kwargs: Any) -> list[dict]:
        """List available serial ports."""
        loop = asyncio.get_running_loop()
        ports = await loop.run_in_executor(None, get_serial_ports)
        return [
            {"port": p.path, "desc": p.description if p.description != "n/a" else p.path}
            for p in ports
        ]

    @api_command("config/get_preferences")
    async def get_prefs(self, **kwargs: Any) -> dict:
        """Get user preferences."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, get_preferences, self._db.settings.config_dir)

    @api_command("config/set_preferences")
    async def set_prefs(self, **kwargs: Any) -> dict:
        """Update user preferences."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, set_preferences, self._db.settings.config_dir, kwargs
        )

    @api_command("config/get_secrets")
    async def get_secrets(self, **kwargs: Any) -> list[str]:
        """Get secret key names from secrets.yaml."""
        loop = asyncio.get_running_loop()

        def _read_secrets() -> list[str]:
            secrets_path = self._db.settings.config_dir / "secrets.yaml"
            if not secrets_path.exists():
                return []
            try:
                data = yaml_util.load_yaml(str(secrets_path))
                return sorted(data.keys()) if isinstance(data, dict) else []
            except Exception:
                return []

        return await loop.run_in_executor(None, _read_secrets)

    @api_command("config/get_info")
    async def get_info(self, *, configuration: str, **kwargs: Any) -> dict | None:
        """Get compiled device metadata (StorageJSON) for a configuration."""
        loop = asyncio.get_running_loop()

        try:
            self._db.settings.rel_path(configuration)
        except ValueError:
            return None

        def _load_info() -> dict | None:
            storage = StorageJSON.load(ext_storage_path(configuration))
            if storage is None:
                return None
            return {
                "name": storage.name,
                "friendly_name": storage.friendly_name,
                "comment": storage.comment,
                "address": storage.address,
                "web_port": storage.web_port,
                "target_platform": storage.target_platform,
                "current_version": storage.esphome_version,
                "deployed_version": storage.firmware_bin_path,
                "loaded_integrations": storage.loaded_integrations,
            }

        return await loop.run_in_executor(None, _load_info)
