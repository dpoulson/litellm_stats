"""Constants for the LiteLLM Cost integration."""
from typing import Final

DOMAIN: Final = "litellm_cost"
NAME: Final = "LiteLLM Cost & Stats"

# Configuration keys
CONF_API_HOST: Final = "api_host"
CONF_API_KEY: Final = "api_key"
CONF_CURRENCY: Final = "currency"
CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_VERIFY_SSL: Final = "verify_ssl"

# Defaults
DEFAULT_API_HOST: Final = "http://localhost:4000"
DEFAULT_CURRENCY: Final = "USD"
DEFAULT_SCAN_INTERVAL: Final = 60  # seconds
DEFAULT_VERIFY_SSL: Final = True

# Supported currencies
SUPPORTED_CURRENCIES: Final = ["USD", "EUR", "GBP", "CAD", "AUD", "JPY", "CNY"]
