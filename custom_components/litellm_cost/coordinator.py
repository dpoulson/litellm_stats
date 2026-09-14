"""DataUpdateCoordinator for LiteLLM Cost integration."""
from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import LiteLLMApiClient, LiteLLMApiError, LiteLLMData
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class LiteLLMDataUpdateCoordinator(DataUpdateCoordinator[LiteLLMData]):
    """Class to manage fetching LiteLLM metrics."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: LiteLLMApiClient,
        update_interval: timedelta,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )
        self.client = client

    async def _async_update_data(self) -> LiteLLMData:
        """Fetch data from LiteLLM."""
        try:
            return await self.client.fetch_all_data()
        except LiteLLMApiError as err:
            raise UpdateFailed(f"Error communicating with LiteLLM proxy: {err}") from err
