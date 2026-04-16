"""Entry point: python -m esphome_device_builder [options]."""

from __future__ import annotations

import argparse
import logging
from logging.handlers import RotatingFileHandler

from .constants import DEFAULT_HOST, DEFAULT_PORT
from .controllers.config import DashboardSettings
from .device_builder import DeviceBuilder

_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_MAX_LOG_SIZE = 5_000_000  # 5 MB
_LOGGER_NAME = "esphome_device_builder"

_LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
}


def _setup_logging(log_level: str, log_file: str | None = None) -> None:
    """Set up logging with console + optional file handler."""
    level = _LOG_LEVELS.get(log_level.lower(), logging.INFO)

    logging.basicConfig(level=level, format=_FORMAT, datefmt=_DATE_FORMAT)

    if log_file:
        file_handler = RotatingFileHandler(log_file, maxBytes=_MAX_LOG_SIZE, backupCount=1)
        file_handler.setFormatter(logging.Formatter(_FORMAT, datefmt=_DATE_FORMAT))
        logging.getLogger().addHandler(file_handler)

    logging.getLogger(_LOGGER_NAME).setLevel(level)

    # Silence noisy libraries
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("zeroconf").setLevel(logging.WARNING)


def main() -> None:
    """Run the ESPHome Device Builder."""
    parser = argparse.ArgumentParser(
        description="ESPHome Device Builder",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "configuration",
        nargs="?",
        default="./configs",
        help="Path to the ESPHome configuration directory",
    )
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="HTTP port to listen on")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Host/IP to bind to")
    parser.add_argument("--username", default="", help="Dashboard username")
    parser.add_argument("--password", default="", help="Dashboard password")
    parser.add_argument("--ha-addon", action="store_true", help="Running as HA add-on")
    parser.add_argument(
        "--log-level",
        default="info",
        choices=["debug", "info", "warning", "error"],
        help="Log level",
    )
    parser.add_argument("--log-file", default=None, help="Log to file (rotated)")

    args = parser.parse_args()

    _setup_logging(args.log_level, args.log_file)

    settings = DashboardSettings()
    settings.parse_args(args)

    device_builder = DeviceBuilder(settings)
    device_builder.run()


if __name__ == "__main__":
    main()
