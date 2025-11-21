from __future__ import annotations
import logging
import json
from typing import Any
from aiohttp import web
from ipaddress import ip_address

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.util.network import is_local

from .const import CONF_SECRET, HEADER_TOKEN
from .device_tracker import SIGNAL_ENSURE

_LOGGER = logging.getLogger(__name__)


def _is_connect(evt: dict[str, Any]) -> bool:
    if evt.get("id"):
        idv = str(evt.get("id", "")).lower()
        return idv == "event.client_connected"
    elif evt.get("name"):
        return evt.get("name") == "WiFi Client Connected"

    return False


def _is_disconnect(evt: dict[str, Any]) -> bool:
    if evt.get("id"):
        idv = str(evt.get("id", "")).lower()
        return idv == "event.client_disconnected"
    elif evt.get("name"):
        return evt.get("name") == "WiFi Client Disconnected"

    return False

def _extract_events(body: dict[str, Any]) -> list[dict] | None:
    if "events" in body:
        return body.get("events")
    elif "parameters" in body:
        parameters = body.get("parameters", {})
        parameters["name"] = body.get("name")
        return [parameters]

    return None


def _extract_mac(evt: dict[str, Any]) -> str | None:
    mac = None
    
    if evt.get("scope"):
        scope = evt.get("scope") or {}
        mac = scope.get("client_device_id") or scope.get("mac")
    elif evt.get("UNIFIclientMac"):
        mac = evt.get("UNIFIclientMac")

    return str(mac).lower() if mac else None

def _extract_ip(evt: dict[str, Any]) -> str | None:
    ip = None
    
    if evt.get("UNIFIclientIp"):
        ip = evt.get("UNIFIclientIp")
        
    return str(ip) if ip else None


def build_webhook_handler(hass: HomeAssistant, entry):
    @callback
    async def _handler(hass: HomeAssistant, webhook_id: str, request):
        secret = (entry.options.get(CONF_SECRET) or "").strip()  # static token
        raw = await request.read()

        try:
            remote_address = ip_address(request.remote)
        except ValueError:
            _LOGGER.error("Invalid remote IP address: %s", request.remote)
            return web.json_response({"status": "bad_request"}, status=400)

        if not is_local(remote_address):
            _LOGGER.warning("unifi_webhook_presence: request from non-local address %s", remote_address)
            return web.json_response({"status": "forbidden"}, status=403)

        # Static token auth
        if secret:
            token = (request.headers.get(HEADER_TOKEN) or "").strip()
            if not token or token != secret:
                _LOGGER.warning("unifi_webhook_presence: invalid or missing X-Webhook-Token")
                return web.json_response({"status": "forbidden"}, status=403)

        try:
            body = json.loads(raw.decode() or "{}")
        except Exception:
            _LOGGER.exception("unifi_webhook_presence: invalid JSON")
            return web.json_response({"status": "bad_request"}, status=400)
        
        _LOGGER.debug("unifi_webhook_presence: received payload: %s", json.dumps(body))

        events = _extract_events(body)
        if not isinstance(events, list) or not events:
            raw_body = json.dumps(body)
            _LOGGER.warning("unifi_webhook_presence: no events in payload. Raw payload: %s", raw_body)
            return web.json_response({"status": "ignored", "reason": "no_events"})

        processed = 0
        for evt in events:
            mac = _extract_mac(evt)
            ip = _extract_ip(evt)
            if not mac:
                continue
            if _is_connect(evt):
                _LOGGER.debug("unifi_webhook_presence: sent connect event for %s", mac)
                async_dispatcher_send(hass, SIGNAL_ENSURE, mac, ip, True)
                processed += 1
            elif _is_disconnect(evt):
                _LOGGER.debug("unifi_webhook_presence: sent disconnect event for %s", mac)
                async_dispatcher_send(hass, SIGNAL_ENSURE, mac, ip, False)
                processed += 1

        if processed == 0:
            raw_events = json.dumps(events)
            _LOGGER.warning("unifi_webhook_presence: no valid connect/disconnect events found. Raw events: %s", raw_events)

        return web.json_response({"status": "ok", "processed": processed})

    return _handler
