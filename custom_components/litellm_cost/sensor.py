"""Sensor platform for LiteLLM Cost integration."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import LiteLLMData
from .const import CONF_API_HOST, CONF_CURRENCY, DEFAULT_CURRENCY, DOMAIN
from .coordinator import LiteLLMDataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class LiteLLMSensorEntityDescription(SensorEntityDescription):
    value_fn: Callable[[LiteLLMData], Any] = lambda _: None
    attrs_fn: Callable[[LiteLLMData], dict[str, Any]] | None = None
    is_supported: Callable[[LiteLLMData], bool] = lambda _: True


SENSOR_DESCRIPTIONS: tuple[LiteLLMSensorEntityDescription, ...] = (
    LiteLLMSensorEntityDescription(
        key="total_spend",
        name="Total Spend",
        icon="mdi:cash-multiple",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda data: round(data.total_spend, 4),
        attrs_fn=lambda data: {
            "healthy": data.healthy,
            "models_spend": data.model_spend,
            "tags_spend": data.tag_spend,
            "keys_count": data.keys_count,
            "users_count": data.users_count,
            "total_tokens": data.total_tokens,
            "prompt_tokens": data.prompt_tokens,
            "completion_tokens": data.completion_tokens,
            "total_requests": data.total_requests,
        },
    ),
    LiteLLMSensorEntityDescription(
        key="key_spend",
        name="Key Spend",
        icon="mdi:key-wireless",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda data: round(data.key_spend, 4) if data.key_spend is not None else None,
        attrs_fn=lambda data: {
            "user_id": data.key_user_id,
            "team_id": data.key_team_id,
            "models": data.key_models,
        },
        is_supported=lambda data: data.key_spend is not None,
    ),
    LiteLLMSensorEntityDescription(
        key="remaining_budget",
        name="Remaining Budget",
        icon="mdi:wallet-outline",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: (
            round(data.key_budget_remaining, 4) if data.key_budget_remaining is not None else None
        ),
        is_supported=lambda data: data.key_budget_remaining is not None,
    ),
    LiteLLMSensorEntityDescription(
        key="budget_usage_ratio",
        name="Budget Usage",
        icon="mdi:percent",
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: (
            round((data.key_spend / data.key_max_budget) * 100, 1)
            if data.key_spend is not None and data.key_max_budget and data.key_max_budget > 0
            else None
        ),
        is_supported=lambda data: (
            data.key_spend is not None and data.key_max_budget is not None and data.key_max_budget > 0
        ),
    ),
    LiteLLMSensorEntityDescription(
        key="today_spend",
        name="Today Spend",
        icon="mdi:calendar-today",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: round(data.today_spend, 4) if data.today_spend is not None else None,
        is_supported=lambda data: data.today_spend is not None,
    ),
    LiteLLMSensorEntityDescription(
        key="total_tokens",
        name="Total Tokens",
        icon="mdi:counter",
        native_unit_of_measurement="tokens",
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda data: data.total_tokens,
        attrs_fn=lambda data: {
            "prompt_tokens": data.prompt_tokens,
            "completion_tokens": data.completion_tokens,
        },
        is_supported=lambda data: data.total_tokens > 0,
    ),
    LiteLLMSensorEntityDescription(
        key="total_requests",
        name="Total Requests",
        icon="mdi:message-badge-outline",
        native_unit_of_measurement="requests",
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda data: data.total_requests,
        attrs_fn=lambda data: {
            "failed_requests": data.failed_requests,
        },
        is_supported=lambda data: data.total_requests > 0,
    ),
    LiteLLMSensorEntityDescription(
        key="active_keys",
        name="Active Keys",
        icon="mdi:key",
        native_unit_of_measurement="keys",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.keys_count,
        is_supported=lambda data: data.keys_count > 0,
    ),
    LiteLLMSensorEntityDescription(
        key="top_model",
        name="Top Model by Spend",
        icon="mdi:brain",
        value_fn=lambda data: (
            max(data.model_spend.items(), key=lambda item: item[1])[0]
            if data.model_spend
            else "None"
        ),
        attrs_fn=lambda data: {"model_spend": data.model_spend},
        is_supported=lambda data: bool(data.model_spend),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up LiteLLM sensors from a config entry."""
    coordinator: LiteLLMDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    currency = entry.data.get(CONF_CURRENCY, DEFAULT_CURRENCY)

    entities: list[LiteLLMSensor] = []
    for description in SENSOR_DESCRIPTIONS:
        if description.is_supported(coordinator.data):
            entities.append(LiteLLMSensor(coordinator, entry, description, currency))

    async_add_entities(entities)


class LiteLLMSensor(CoordinatorEntity[LiteLLMDataUpdateCoordinator], SensorEntity):
    """Representation of a LiteLLM sensor entity."""

    entity_description: LiteLLMSensorEntityDescription

    def __init__(
        self,
        coordinator: LiteLLMDataUpdateCoordinator,
        entry: ConfigEntry,
        description: LiteLLMSensorEntityDescription,
        currency: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_has_entity_name = True

        if description.device_class == SensorDeviceClass.MONETARY:
            self._attr_native_unit_of_measurement = currency

        api_host = entry.data.get(CONF_API_HOST, "LiteLLM")
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"LiteLLM Proxy ({api_host})",
            manufacturer="LiteLLM",
            model="AI Gateway Proxy",
            configuration_url=api_host,
        )

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        if self.entity_description.attrs_fn:
            return self.entity_description.attrs_fn(self.coordinator.data)
        return None
