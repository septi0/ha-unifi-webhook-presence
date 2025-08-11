from __future__ import annotations
import logging

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.components import webhook as ha_webhook
from homeassistant.helpers.storage import Store

from .const import DOMAIN, CONF_WEBHOOK_ID, STORAGE_VERSION, STORAGE_KEY_FMT
from .webhook import build_webhook_handler

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = ["device_tracker"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up UniFi Webhook Presence from a config entry."""
    wh_id = entry.data[CONF_WEBHOOK_ID]

    # Register the webhook endpoint using HA's webhook component
    ha_webhook.async_register(
        hass,
        DOMAIN,
        "UniFi Webhook Presence",
        wh_id,
        build_webhook_handler(hass, entry),
    )
    entry.async_on_unload(lambda: ha_webhook.async_unregister(hass, wh_id))

    # Set up the device_tracker platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    ha_webhook.async_unregister(hass, entry.data[CONF_WEBHOOK_ID])
    return ok

async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove the entry and clean up resources."""
    _LOGGER.debug("Cleaning up storage for %s", DOMAIN)
    
    store = Store(hass, STORAGE_VERSION, STORAGE_KEY_FMT.format(entry_id=entry.entry_id))
    
    try:
        # This will delete the storage file
        await store.async_remove()
        _LOGGER.info("Successfully removed storage file for %s", DOMAIN)
    except Exception as e:
        _LOGGER.warning("Failed to remove storage file: %s", e)