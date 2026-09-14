"""Unit tests for LiteLLMDataUpdateCoordinator."""
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.litellm_cost.api import LiteLLMApiClient, LiteLLMApiError, LiteLLMData
from custom_components.litellm_cost.coordinator import LiteLLMDataUpdateCoordinator
from homeassistant.helpers.update_coordinator import UpdateFailed


@pytest.mark.asyncio
async def test_coordinator_fetch_success():
    """Test successful data update through coordinator."""
    hass = MagicMock()
    client = MagicMock(spec=LiteLLMApiClient)
    client.fetch_all_data = AsyncMock(
        return_value=LiteLLMData(total_spend=42.50, key_spend=10.0)
    )

    coordinator = LiteLLMDataUpdateCoordinator(
        hass=hass,
        client=client,
        update_interval=timedelta(seconds=60),
    )

    data = await coordinator._async_update_data()
    assert data.total_spend == 42.50
    assert data.key_spend == 10.0


@pytest.mark.asyncio
async def test_coordinator_fetch_failure():
    """Test coordinator handles API errors by raising UpdateFailed."""
    hass = MagicMock()
    client = MagicMock(spec=LiteLLMApiClient)
    client.fetch_all_data = AsyncMock(side_effect=LiteLLMApiError("Connection lost"))

    coordinator = LiteLLMDataUpdateCoordinator(
        hass=hass,
        client=client,
        update_interval=timedelta(seconds=60),
    )

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()
