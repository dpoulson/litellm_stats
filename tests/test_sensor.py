"""Unit tests for LiteLLM sensor definitions."""
from unittest.mock import MagicMock

import pytest

from custom_components.litellm_cost.api import LiteLLMData
from custom_components.litellm_cost.const import CONF_API_HOST, CONF_CURRENCY, DOMAIN
from custom_components.litellm_cost.sensor import SENSOR_DESCRIPTIONS, LiteLLMSensor


def test_sensor_values_and_support():
    """Test sensor value functions and support predicates."""
    data = LiteLLMData(
        healthy=True,
        total_spend=123.4567,
        key_spend=45.6789,
        key_max_budget=100.0,
        key_budget_remaining=54.3211,
        keys_count=5,
        today_spend=3.5,
        model_spend={"gpt-4o": 30.0, "claude-3-5-sonnet": 15.67},
        tag_spend={"production": 40.0},
    )

    sensors_map = {desc.key: desc for desc in SENSOR_DESCRIPTIONS}

    assert sensors_map["total_spend"].value_fn(data) == 123.4567
    assert sensors_map["key_spend"].value_fn(data) == 45.6789
    assert sensors_map["remaining_budget"].value_fn(data) == 54.3211
    assert sensors_map["budget_usage_ratio"].value_fn(data) == 45.7
    assert sensors_map["today_spend"].value_fn(data) == 3.5
    assert sensors_map["active_keys"].value_fn(data) == 5
    assert sensors_map["top_model"].value_fn(data) == "gpt-4o"

    # Attributes check
    attrs = sensors_map["total_spend"].attrs_fn(data)
    assert attrs["healthy"] is True
    assert attrs["keys_count"] == 5


def test_sensor_entity_instantiation():
    """Test LiteLLMSensor entity properties."""
    coordinator = MagicMock()
    coordinator.data = LiteLLMData(total_spend=99.99)

    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.data = {CONF_API_HOST: "http://localhost:4000", CONF_CURRENCY: "USD"}

    sensors_map = {desc.key: desc for desc in SENSOR_DESCRIPTIONS}
    desc = sensors_map["total_spend"]

    sensor = LiteLLMSensor(coordinator, entry, desc, "USD")
    assert sensor._attr_unique_id == "test_entry_id_total_spend"
    assert sensor._attr_native_unit_of_measurement == "USD"
    assert sensor.native_value == 99.99
