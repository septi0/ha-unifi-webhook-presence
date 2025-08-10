from __future__ import annotations
import logging

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.components import webhook as ha_webhook

from .const import DOMAIN, CONF_WEBHOOK_ID
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
