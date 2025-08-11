# Home Assistant UniFi Webhook Presence

A Home Assistant integration that tracks client devices from your UniFi Controller using **webhooks**. This integration eliminates the need to expose your gateway or controller directly to your Home Assistant instance.

## Highlights
- **Local push** (no polling) via HA’s `/api/webhook/*`
- **Auto-discovery**: new MACs create entities on their first event
- **Graceful “away”**: configurable disconnect delay to avoid flapping
- **Persists entities** across restarts (no “no longer provided” banner)
- **Entity-only** (no Devices), enabled by default
- **Secured** by the `X-Webhook-Token` header (shared secret), unique webhook URL per instance, local-only webhook access

## How it works (data flow)
1. **UniFi Controller** detects a client device connecting or disconnecting.
2. **UniFi Controller** sends a webhook event to Home Assistant with the device’s MAC address and connection status.
3. **Home Assistant** receives the webhook event and updates the corresponding **device_tracker** entity.

Home Assistant never connects to or polls the UniFi Controller. **Only the controller pushes** events to HA via the configured webhook action.

## Install
1. Copy this folder to:
       
       custom_components/unifi_webhook_presence/
       
   (Same place as `configuration.yaml`.)
2. **Restart Home Assistant.**
3. In HA: **Settings → Devices & Services → Add Integration → “UniFi Webhook Presence”.**
4. Enter:
   - **Secret (token)** — required (used in `X-Webhook-Token`)
   - **Disconnect delay** — seconds before marking `not_home`
5. **Save** the integration.
6. Open **integration settings** to grab the generated webhook URL.

## Usage

### Configure UniFi (Alarm Manager → Webhook)
1. In your **UniFi Controller**, open **Alarm Manager**.
2. Click **New Alarm**.
3. **Trigger:** select **Monitoring**.
4. **Events to monitor:** check:
   - **Client device connected**
   - **Client device disconnected**
5. **Action:** choose **Webhook** and configure:
   - URL: **Generated Webhook URL**

   - Headers: **X-Webhook-Token: <your_secret>**

     Use the same secret you set in the integration.
6. **Save** the alarm.

### Verify
- Toggle Wi-Fi on a device. A new `device_tracker` entity will be created automatically and switch to **home** on connect and **not_home** after the configured delay on disconnect.
