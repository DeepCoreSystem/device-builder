"""Device-related data models."""

from __future__ import annotations

from dataclasses import dataclass

from mashumaro.mixins.orjson import DataClassORJSONMixin


@dataclass
class ConfiguredDevice(DataClassORJSONMixin):
    name: str
    friendly_name: str
    configuration: str
    path: str
    comment: str | None
    address: str
    web_port: int | None
    target_platform: str
    current_version: str
    deployed_version: str
    loaded_integrations: list[str]
    board_id: str = ""


@dataclass
class AdoptableDevice(DataClassORJSONMixin):
    name: str
    friendly_name: str
    package_import_url: str
    project_name: str
    project_version: str
    network: str
    ignored: bool


@dataclass
class DevicesResponse(DataClassORJSONMixin):
    configured: list[ConfiguredDevice]
    importable: list[AdoptableDevice]


@dataclass
class WizardRequest(DataClassORJSONMixin):
    name: str
    ssid: str
    psk: str
    type: str  # "basic" | "upload" | "empty"
    platform: str | None = None
    board: str | None = None
    password: str | None = None
    file_content: str | None = None
    board_id: str | None = None


@dataclass
class WizardResponse(DataClassORJSONMixin):
    configuration: str


@dataclass
class UpdateDeviceRequest(DataClassORJSONMixin):
    friendly_name: str | None = None
    comment: str | None = None
    board_id: str | None = None


@dataclass
class UpdateDeviceResponse(DataClassORJSONMixin):
    name: str
    friendly_name: str
    comment: str | None
    board_id: str | None


@dataclass
class ImportRequest(DataClassORJSONMixin):
    name: str
    project_name: str
    package_import_url: str
    friendly_name: str | None = None
    encryption: str | None = None


@dataclass
class IgnoreDeviceRequest(DataClassORJSONMixin):
    name: str
    ignore: bool
