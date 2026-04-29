"""
Device connectivity monitor — mDNS browser + ping fallback.

Tracks online/offline state for the configured devices, with mDNS as
the primary source (event-driven) and ICMP ping as a periodic fallback
for devices that aren't broadcasting their service. The monitor calls
back into the owning controller whenever a state actually changes;
controllers stay free of zeroconf / icmplib details.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from esphome.zeroconf import AsyncEsphomeZeroconf

try:
    from icmplib import async_ping as icmp_ping
except ImportError:  # pragma: no cover — icmplib is optional
    icmp_ping = None  # type: ignore[assignment]

from ..models import Device, DeviceState

_LOGGER = logging.getLogger(__name__)
_ESPHOME_SERVICE_TYPE = "_esphomelib._tcp.local."
_PING_INTERVAL = 60  # seconds between ping sweeps
_PING_BATCH_SIZE = 10

# Callback signature used by DeviceStateMonitor to push state changes
# back to its owner. The owner decides what to do with the new state
# (e.g. fire a bus event, mutate the device model).
StateChangeCallback = Callable[[str, DeviceState, str], None]


class DeviceStateMonitor:
    """
    Drive device state from mDNS broadcasts plus periodic ICMP pings.

    Only one source can own a device's state at a time. mDNS always
    wins; ping only writes when mDNS hasn't already resolved the
    device. The ``priority_for(name)`` API lets callers query which
    source is currently authoritative.
    """

    def __init__(
        self,
        get_devices: Callable[[], list[Device]],
        on_state_change: StateChangeCallback,
    ) -> None:
        self._get_devices = get_devices
        self._on_state_change = on_state_change
        self._state_source: dict[str, str] = {}  # device name → "mdns" | "ping"
        self._zeroconf: AsyncEsphomeZeroconf | None = None
        self._mdns_browser: Any = None
        self._ping_task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the mDNS browser and the periodic ping sweep."""
        await self._start_mdns_browser()
        self._ping_task = asyncio.create_task(self._ping_loop())

    async def stop(self) -> None:
        """Tear down the browser and cancel the ping loop."""
        if self._ping_task is not None:
            self._ping_task.cancel()
            self._ping_task = None
        if self._mdns_browser is not None:
            try:
                await self._mdns_browser.async_cancel()
            except Exception:
                _LOGGER.debug("mDNS browser cancel failed", exc_info=True)
            self._mdns_browser = None
        if self._zeroconf is not None:
            try:
                await self._zeroconf.async_close()
            except Exception:
                _LOGGER.debug("zeroconf close failed", exc_info=True)
            self._zeroconf = None

    def priority_for(self, name: str) -> str:
        """Return the source currently authoritative for *name* (or "unknown")."""
        return self._state_source.get(name, "unknown")

    def apply(self, name: str, state: DeviceState, source: str) -> bool:
        """
        Record a state observation from *source*.

        Returns True when the observation actually changed the device's
        state and the change was forwarded to the callback. mDNS always
        wins over ping; same-state observations are no-ops.
        """
        device = self._find_device_by_name(name)
        if device is None:
            _LOGGER.debug(
                "Device %s not in catalog — ignoring %s state from %s", name, state, source
            )
            return False

        current_source = self._state_source.get(name, "unknown")
        if source == "ping" and current_source == "mdns":
            return False
        if device.state == state:
            return False

        self._state_source[name] = source
        self._on_state_change(name, state, source)
        return True

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _find_device_by_name(self, name: str) -> Device | None:
        for device in self._get_devices():
            if device.name == name:
                return device
        return None

    async def _start_mdns_browser(self) -> None:
        try:
            from zeroconf import ServiceStateChange
            from zeroconf.asyncio import AsyncServiceBrowser
        except ImportError:
            _LOGGER.warning("zeroconf not available — mDNS device discovery disabled")
            return

        try:
            self._zeroconf = AsyncEsphomeZeroconf()
        except Exception:
            _LOGGER.exception("Could not start zeroconf — falling back to ping only")
            self._zeroconf = None
            return

        loop = asyncio.get_running_loop()

        def _on_service_state_change(
            zeroconf: Any, service_type: str, name: str, state_change: ServiceStateChange
        ) -> None:
            # mDNS reports "<my-device>._esphomelib._tcp.local." — strip
            # the service suffix and convert hyphens (mDNS) back to
            # underscores (YAML config naming).
            device_name = name.split(".")[0].replace("-", "_")
            _LOGGER.debug("mDNS: %s %s (raw: %s)", state_change, device_name, name)

            # zeroconf callbacks fire on a different thread — bounce the
            # state update back to the asyncio loop.
            if state_change in (ServiceStateChange.Added, ServiceStateChange.Updated):
                loop.call_soon_threadsafe(self.apply, device_name, DeviceState.ONLINE, "mdns")
            elif state_change == ServiceStateChange.Removed:
                loop.call_soon_threadsafe(self.apply, device_name, DeviceState.OFFLINE, "mdns")
                self._state_source.pop(device_name, None)

        try:
            self._mdns_browser = AsyncServiceBrowser(
                self._zeroconf.zeroconf,
                _ESPHOME_SERVICE_TYPE,
                handlers=[_on_service_state_change],
            )
            _LOGGER.info("mDNS browser started for %s", _ESPHOME_SERVICE_TYPE)
        except Exception:
            _LOGGER.exception("Could not start mDNS browser — device discovery limited to ping")

    async def _ping_loop(self) -> None:
        try:
            while True:
                await asyncio.sleep(_PING_INTERVAL)
                await self._ping_sweep()
        except asyncio.CancelledError:
            pass

    async def _ping_sweep(self) -> None:
        if icmp_ping is None:
            return

        devices_to_ping = [
            d
            for d in self._get_devices()
            if d.address and self._state_source.get(d.name, "unknown") != "mdns"
        ]
        if not devices_to_ping:
            return

        _LOGGER.debug("Pinging %d devices", len(devices_to_ping))

        for i in range(0, len(devices_to_ping), _PING_BATCH_SIZE):
            batch = devices_to_ping[i : i + _PING_BATCH_SIZE]
            tasks = [self._ping_device(d) for d in batch]
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _ping_device(self, device: Device) -> None:
        try:
            result = await icmp_ping(device.address, count=1, timeout=3, privileged=False)
        except Exception:
            return
        new_state = DeviceState.ONLINE if result.is_alive else DeviceState.OFFLINE
        self.apply(device.name, new_state, "ping")
