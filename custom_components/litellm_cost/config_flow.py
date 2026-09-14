"""Config flow for LiteLLM Cost integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import voluptuous as vol

from .api import LiteLLMApiClient, LiteLLMAuthError, LiteLLMConnectionError
from .const import (
    CONF_API_HOST,
    CONF_API_KEY,
    CONF_CURRENCY,
    CONF_SCAN_INTERVAL,
    CONF_VERIFY_SSL,
    DEFAULT_API_HOST,
    DEFAULT_CURRENCY,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
    SUPPORTED_CURRENCIES,
)

_LOGGER = logging.getLogger(__name__)


class LiteLLMConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for LiteLLM Cost."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            api_host = user_input[CONF_API_HOST].strip().rstrip("/")
            api_key = user_input.get(CONF_API_KEY, "").strip() or None
            currency = user_input.get(CONF_CURRENCY, DEFAULT_CURRENCY)
            scan_interval = user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            verify_ssl = user_input.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)

            session = async_get_clientsession(self.hass, verify_ssl=verify_ssl)
            client = LiteLLMApiClient(
                base_url=api_host,
                api_key=api_key,
                session=session,
                verify_ssl=verify_ssl,
            )

            try:
                await client.check_health()
                if api_key:
                    await client.get_key_info()
            except LiteLLMAuthError:
                errors["base"] = "invalid_auth"
            except LiteLLMConnectionError:
                errors["base"] = "cannot_connect"
            except Exception as err:
                _LOGGER.exception("Unexpected exception during LiteLLM validation: %s", err)
                errors["base"] = "unknown"
            else:
                unique_id = f"{api_host}_{api_key[-6:] if api_key else 'anonymous'}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                title = f"LiteLLM ({api_host})"
                return self.async_create_entry(
                    title=title,
                    data={
                        CONF_API_HOST: api_host,
                        CONF_API_KEY: api_key,
                        CONF_CURRENCY: currency,
                        CONF_SCAN_INTERVAL: scan_interval,
                        CONF_VERIFY_SSL: verify_ssl,
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_API_HOST, default=DEFAULT_API_HOST): str,
                vol.Optional(CONF_API_KEY, default=""): str,
                vol.Optional(CONF_CURRENCY, default=DEFAULT_CURRENCY): vol.In(SUPPORTED_CURRENCIES),
                vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
                    vol.Coerce(int), vol.Range(min=10, max=86400)
                ),
                vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): bool,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return LiteLLMOptionsFlowHandler(config_entry)


class LiteLLMOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for LiteLLM."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_currency = self._config_entry.options.get(
            CONF_CURRENCY,
            self._config_entry.data.get(CONF_CURRENCY, DEFAULT_CURRENCY),
        )
        current_scan_interval = self._config_entry.options.get(
            CONF_SCAN_INTERVAL,
            self._config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )

        options_schema = vol.Schema(
            {
                vol.Optional(CONF_CURRENCY, default=current_currency): vol.In(SUPPORTED_CURRENCIES),
                vol.Optional(CONF_SCAN_INTERVAL, default=current_scan_interval): vol.All(
                    vol.Coerce(int), vol.Range(min=10, max=86400)
                ),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
        )
