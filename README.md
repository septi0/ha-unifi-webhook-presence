# Home Assistant UniFi Webhook Presence

Lightweight Home Assistant custom integration that turns **Client connect/disconnect webhooks** from your UniFi Controller into **device_tracker** entities you can assign to People without exposing the gateway/controller directly to your Home Assistant instance.

## Highlights
- **Local push** (no polling) via HA’s `/api/webhook/*`
- **Auto-discover**: new MACs create entities on first event
- **Graceful “away”**: configurable disconnect delay to avoid flapping
- **Persists entities** across restarts (no “no longer provided” banner)
- **Entity-only** (no Devices), enabled by default
- **Secured** by `X-Webhook-Token` header (shared secret)

## Install
1. Copy this folder to:
       
       custom_components/unifi_webhook_presence/
       
   (Same place as `configuration.yaml`.)
2. **Restart Home Assistant.**
3. In HA: **Settings → Devices & Services → Add Integration → “UniFi Webhook Presence”.**
4. Enter:
   - **Secret (token)** — required (used in `X-Webhook-Token`)
   - **Disconnect delay** — seconds before marking `not_home`

## Usage

### Configure UniFi (Alarm Manager → Webhook)
1. In your **UniFi Controller**, open **Alarm Manager**.
2. Click **New Alarm**.
3. **Trigger:** select **Monitoring**.
4. **Events to monitor:** check:
   - **Client device connected**
   - **Client device disconnected**
5. **Action:** choose **Webhook** and configure:
   - **URL:**  
     
         http(s)://<ha-instance>/api/webhook/unifi_webhook_presence
     
     Replace `<ha-instance>` with your Home Assistant base URL or IP. HTTPS is recommended.
   - **Headers:** add:
     
         X-Webhook-Token: <your_secret>
     
     Use the same secret you set in the integration.
6. **Save** the alarm.

### Verify
- Toggle Wi-Fi on a device. A new `device_tracker` entity will be created automatically and switch to **home** on connect and **not_home** after the configured delay on disconnect.