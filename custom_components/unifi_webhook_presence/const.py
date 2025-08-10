DOMAIN = "unifi_webhook_presence"

# Config keys
CONF_WEBHOOK_ID = "webhook_id"
CONF_SECRET = "secret"                  # used as a static token now
CONF_DISCONNECT_DELAY = "disconnect_delay"
CONF_DEVICES = "devices"                # list of {mac, name, dev_id}

# Defaults
DEFAULT_DISCONNECT_DELAY = 120          # seconds

# Headers
HEADER_TOKEN = "X-Webhook-Token"