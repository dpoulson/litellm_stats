"""Unit tests for LiteLLM config flow."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.litellm_cost.api import LiteLLMAuthError, LiteLLMConnectionError
from custom_components.litellm_cost.config_flow import LiteLLMConfigFlow, LiteLLMOptionsFlowHandler
from custom_components.litellm_cost.const import (
    CONF_API_HOST,
    CONF_API_KEY,
    CONF_CURRENCY,
    CONF_SCAN_INTERVAL,
)


@pytest.mark.asyncio
async def test_config_flow_user_form():
    """Test initial form is shown when user_input is None."""
    flow = LiteLLMConfigFlow()
    flow.hass = MagicMock()

    result = await flow.async_step_user(user_input=None)
    assert result["type"] == "form" or result.get("step_id") == "user"


@pytest.mark.asyncio
async def test_config_flow_success():
    """Test successful config flow."""
    flow = LiteLLMConfigFlow()
    flow.hass = MagicMock()
    flow.async_set_unique_id = AsyncMock()
    flow._abort_if_unique_id_configured = MagicMock()

    with patch(
        "custom_components.litellm_cost.config_flow.LiteLLMApiClient.check_health",
        new=AsyncMock(return_value=True),
    ), patch(
        "custom_components.litellm_cost.config_flow.LiteLLMApiClient.get_key_info",
        new=AsyncMock(return_value={"spend": 10.0}),
    ):
        result = await flow.async_step_user(
            {
                CONF_API_HOST: "http://localhost:4000",
                CONF_API_KEY: "sk-valid-key",
                CONF_CURRENCY: "USD",
                CONF_SCAN_INTERVAL: 60,
            }
        )
        assert result["type"] == "create_entry" or "data" in result
        assert result["data"][CONF_API_HOST] == "http://localhost:4000"
        assert result["data"][CONF_API_KEY] == "sk-valid-key"


@pytest.mark.asyncio
async def test_config_flow_invalid_auth():
    """Test auth error in config flow."""
    flow = LiteLLMConfigFlow()
    flow.hass = MagicMock()

    with patch(
        "custom_components.litellm_cost.config_flow.LiteLLMApiClient.check_health",
        new=AsyncMock(side_effect=LiteLLMAuthError("Invalid key")),
    ):
        result = await flow.async_step_user(
            {
                CONF_API_HOST: "http://localhost:4000",
                CONF_API_KEY: "sk-invalid",
                CONF_CURRENCY: "USD",
                CONF_SCAN_INTERVAL: 60,
            }
        )
        assert result["errors"]["base"] == "invalid_auth"


@pytest.mark.asyncio
async def test_config_flow_cannot_connect():
    """Test connection error in config flow."""
    flow = LiteLLMConfigFlow()
    flow.hass = MagicMock()

    with patch(
        "custom_components.litellm_cost.config_flow.LiteLLMApiClient.check_health",
        new=AsyncMock(side_effect=LiteLLMConnectionError("Connection refused")),
    ):
        result = await flow.async_step_user(
            {
                CONF_API_HOST: "http://localhost:4000",
                CONF_API_KEY: "",
                CONF_CURRENCY: "USD",
                CONF_SCAN_INTERVAL: 60,
            }
        )
        assert result["errors"]["base"] == "cannot_connect"


@pytest.mark.asyncio
async def test_options_flow():
    """Test options flow initialization and update."""
    entry = MagicMock()
    entry.options = {CONF_CURRENCY: "USD", CONF_SCAN_INTERVAL: 60}
    entry.data = {CONF_CURRENCY: "USD", CONF_SCAN_INTERVAL: 60}

    handler = LiteLLMOptionsFlowHandler(entry)
    res_form = await handler.async_step_init(None)
    assert res_form["step_id"] == "init"

    res_submit = await handler.async_step_init({CONF_CURRENCY: "GBP", CONF_SCAN_INTERVAL: 120})
    assert res_submit["data"][CONF_CURRENCY] == "GBP"
    assert res_submit["data"][CONF_SCAN_INTERVAL] == 120
