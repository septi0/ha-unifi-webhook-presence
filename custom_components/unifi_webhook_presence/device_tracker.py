# /config/custom_components/unifi_webhook_presence/device_tracker.py
from __future__ import annotations

import asyncio
import logging
from typing import Dict, List, Set

from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.storage import Store
from homeassistant.helpers.entity_registry import RegistryEntryDisabler

from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import ScannerEntity

from .const import DOMAIN, CONF_DISCONNECT_DELAY

_LOGGER = logging.getLogger(__name__)

# Dispatcher signal used by the webhook to ensure (create/update) a tracker
SIGNAL_ENSURE = f"{DOMAIN}_ensure"  # payload: (mac: str, is_connected: bool)

STORAGE_VERSION = 1
STORAGE_KEY_FMT = f"{DOMAIN}" + "_data"


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the device_tracker platform for UniFi Webhook Presence."""
    index: Dict[str, WifiPresenceScanner] = {}
    disconnect_delay = int(entry.options.get(CONF_DISCONNECT_DELAY, entry.data.get(CONF_DISCONNECT_DELAY, 120)))

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {"entities_by_mac": index}

    # ---- Persistent store of discovered MACs ----
    store = Store(hass, STORAGE_VERSION, STORAGE_KEY_FMT.format(entry_id=entry.entry_id))
    stored: dict = await store.async_load() or {"macs": []}
    stored_macs: Set[str] = {m.lower() for m in stored.get("macs", [])}

    # # ---- Recreate entities from storage ----
    to_add: List[WifiPresenceScanner] = []
    for mac in sorted(stored_macs):
        if mac in index:
            continue
        ent = WifiPresenceScanner(
            mac=mac,
            name=mac,
            dev_id=mac.replace(":", ""),
            disconnect_delay=disconnect_delay,
        )
        index[mac] = ent
        to_add.append(ent)

    if to_add:
        async_add_entities(to_add, True)
        await store.async_save({"macs": sorted(stored_macs)})
        
    registry = er.async_get(hass)

    # Auto-discover/create new entities
    @callback
    def _ensure(mac: str, is_connected: bool) -> None:
        mac_l = mac.lower()
        ent = index.get(mac_l)
        if ent is None:
            ent = WifiPresenceScanner(
                mac=mac_l,
                name='uwp_' + mac_l,
                dev_id=mac_l.replace(":", ""),
                disconnect_delay=disconnect_delay,
            )
            ent.set_initial_state(is_connected)
            index[mac_l] = ent
            async_add_entities([ent])


            # Persist the new MAC so it exists on next restart
            if mac_l not in stored_macs:
                stored_macs.add(mac_l)
                hass.create_task(store.async_save({"macs": sorted(stored_macs)}))
        else:
            ent.receive_update(is_connected)

    entry.async_on_unload(async_dispatcher_connect(hass, SIGNAL_ENSURE, _ensure))

class WifiPresenceScanner(ScannerEntity, RestoreEntity):
    """A Wi-Fi presence scanner entity backed by webhook events (entity-only, no Device)."""

    _attr_should_poll = False
    _attr_source_type = SourceType.ROUTER
    _attr_entity_registry_enabled_default = True

    def __init__(self, mac: str, name: str, dev_id: str, disconnect_delay: int) -> None:
        # Identity
        self._mac = mac
        self._attr_name = name
        self._attr_unique_id = f"unifi_webhook_presence_{mac}"
        self._dev_id = dev_id
        self._disconnect_delay = disconnect_delay

        # State
        self._attr_is_connected: bool | None = None  # Unknown until restore/event
        self._pending_task: asyncio.Task | None = None
        
    @property
    def entity_registry_enabled_default(self) -> bool:
        return True

    # ---- ScannerEntity required properties ----
    @property
    def is_connected(self) -> bool | None:
        return self._attr_is_connected

    @property
    def mac_address(self) -> str | None:
        return self._mac

    @property
    def ip_address(self) -> str | None:
        # We don't track IP from the webhook (could be added later if provided).
        return None

    # ---- Helpers used by platform/webhook ----
    def set_initial_state(self, is_connected: bool) -> None:
        """Set the very first state prior to adding the entity to HA."""
        self._attr_is_connected = bool(is_connected)

    @callback
    def receive_update(self, is_connected: bool) -> None:
        """Receive an update from the webhook (connect/disconnect)."""
        # cancel any pending delayed "away"
        if self._pending_task and not self._pending_task.done():
            self._pending_task.cancel()
            self._pending_task = None

        if is_connected:
            self._attr_is_connected = True
            self.async_write_ha_state()
        else:
            async def _go_away():
                try:
                    await asyncio.sleep(self._disconnect_delay)
                    self._attr_is_connected = False
                    self.async_write_ha_state()
                except asyncio.CancelledError:
                    return

            self._pending_task = asyncio.create_task(_go_away())

    # ---- Entity lifecycle ----
    async def async_added_to_hass(self) -> None:
        # Restore previous state if we didn't get an initial event
        last = await self.async_get_last_state()
        if last and self._attr_is_connected is None:
            st = str(last.state).lower()
            if st == "home":
                self._attr_is_connected = True
            elif st == "not_home":
                self._attr_is_connected = False

    async def async_will_remove_from_hass(self) -> None:
        if self._pending_task and not self._pending_task.done():
            self._pending_task.cancel()

    @property
    def extra_state_attributes(self):
        return {
            "mac": self._mac,
            "dev_id": self._dev_id,
        }
