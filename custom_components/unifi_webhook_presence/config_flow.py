from __future__ import annotations
import secrets
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.network import get_url

from .const import (
    DOMAIN,
    CONF_WEBHOOK_ID,
    CONF_SECRET,
    CONF_DISCONNECT_DELAY,
    DEFAULT_DISCONNECT_DELAY,
)

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    
    def __init__(self) -> None:
        self._data: dict | None = None
        self._options: dict | None = None

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            webhook_id = secrets.token_hex(12)
            self._data = {
                CONF_WEBHOOK_ID: webhook_id,
            }
            self._options = {
                CONF_SECRET: user_input.get(CONF_SECRET, ""),
                CONF_DISCONNECT_DELAY: user_input.get(CONF_DISCONNECT_DELAY, DEFAULT_DISCONNECT_DELAY),
            }
            return await self.async_step_confirm()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_SECRET): str,
                vol.Optional(CONF_DISCONNECT_DELAY, default=DEFAULT_DISCONNECT_DELAY): int,
            }),
        )

    async def async_step_confirm(self, user_input=None):
        base_url = get_url(self.hass, allow_ip=True)
        webhook_id = self._data[CONF_WEBHOOK_ID]
        webhook_url = f"{base_url}/api/webhook/{webhook_id}"

        if user_input is not None:
            return self.async_create_entry(
                title="UniFi Webhook Presence",
                data=self._data,
                options=self._options,
            )

        return self.async_show_form(
            step_id="confirm",
            description_placeholders={"webhook_url": webhook_url},
            data_schema=vol.Schema({}),
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, entry):
        self.entry = entry

    async def async_step_init(self, user_input=None):
        # Always use entry.options for configurable data
        current_options = self.entry.options

        if user_input is not None:
            return self.async_create_entry(
                title="",
                data={
                    CONF_SECRET: user_input.get(CONF_SECRET, current_options.get(CONF_SECRET, "")),
                    CONF_DISCONNECT_DELAY: user_input.get(CONF_DISCONNECT_DELAY, current_options.get(CONF_DISCONNECT_DELAY, DEFAULT_DISCONNECT_DELAY)),
                },
            )
        
        base_url = get_url(self.hass, allow_ip=True)
        webhook_id = self.entry.data.get(CONF_WEBHOOK_ID)
        webhook_url = f"{base_url}/api/webhook/{webhook_id}"

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(CONF_SECRET, default=current_options.get(CONF_SECRET, "")): str,
                vol.Optional(CONF_DISCONNECT_DELAY, default=current_options.get(CONF_DISCONNECT_DELAY, DEFAULT_DISCONNECT_DELAY)): int,
            }),
            description_placeholders={"webhook_url": webhook_url},
        )