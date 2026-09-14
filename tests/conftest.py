"""Pytest configuration and Home Assistant module mocks."""
import os
import sys
from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"

# Setup base module mocks
homeassistant = MagicMock()
config_entries = MagicMock()
core = MagicMock()
data_entry_flow = MagicMock()
helpers = MagicMock()
aiohttp_client = MagicMock()
device_registry = MagicMock()
entity_platform = MagicMock()
update_coordinator = MagicMock()
components = MagicMock()
sensor = MagicMock()

sys.modules["homeassistant"] = homeassistant
sys.modules["homeassistant.config_entries"] = config_entries
sys.modules["homeassistant.const"] = MagicMock()
sys.modules["homeassistant.core"] = core
sys.modules["homeassistant.data_entry_flow"] = data_entry_flow
sys.modules["homeassistant.helpers"] = helpers
sys.modules["homeassistant.helpers.aiohttp_client"] = aiohttp_client
sys.modules["homeassistant.helpers.device_registry"] = device_registry
sys.modules["homeassistant.helpers.entity_platform"] = entity_platform
sys.modules["homeassistant.helpers.update_coordinator"] = update_coordinator
sys.modules["homeassistant.components"] = components
sys.modules["homeassistant.components.sensor"] = sensor

# Wire package attributes to match sys.modules
homeassistant.config_entries = config_entries
homeassistant.core = core
homeassistant.helpers = helpers
homeassistant.components = components

@dataclass(frozen=True, kw_only=True)
class MockSensorEntityDescription:
    key: str
    name: str | None = None
    icon: str | None = None
    device_class: Any = None
    state_class: Any = None
    native_unit_of_measurement: str | None = None

class MockSensorEntity:
    def __init__(self):
        self.entity_description = None
        self._attr_unique_id = None
        self._attr_native_unit_of_measurement = None
        self._attr_device_info = None

class MockCoordinatorEntity:
    def __init__(self, coordinator):
        self.coordinator = coordinator

    def __class_getitem__(cls, item):
        return cls

class MockDataUpdateCoordinator:
    def __init__(self, hass, logger, name, update_interval):
        self.hass = hass
        self.logger = logger
        self.name = name
        self.update_interval = update_interval
        self.data = None

    def __class_getitem__(cls, item):
        return cls

class MockUpdateFailed(Exception):
    pass

class MockConfigFlow:
    def __init_subclass__(cls, domain=None, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.domain = domain

    def __init__(self):
        self.hass = None
        self.unique_id = None

    def async_show_form(self, step_id, data_schema=None, errors=None, description_placeholders=None):
        return {"type": "form", "step_id": step_id, "data_schema": data_schema, "errors": errors or {}}

    def async_create_entry(self, title, data):
        return {"type": "create_entry", "title": title, "data": data}

    async def async_set_unique_id(self, unique_id=None, raise_on_progress=True):
        self.unique_id = unique_id

    def _abort_if_unique_id_configured(self, updates=None, reload_on_update=True):
        pass

class MockOptionsFlow:
    def __init__(self, *args, **kwargs):
        pass

    def async_show_form(self, step_id, data_schema=None, errors=None):
        return {"type": "form", "step_id": step_id, "data_schema": data_schema, "errors": errors or {}}

    def async_create_entry(self, title, data):
        return {"type": "create_entry", "title": title, "data": data}

def callback_decorator(func):
    return func

core.callback = callback_decorator
config_entries.ConfigFlow = MockConfigFlow
config_entries.OptionsFlow = MockOptionsFlow

sensor.SensorEntityDescription = MockSensorEntityDescription
sensor.SensorEntity = MockSensorEntity
sensor.SensorDeviceClass = MagicMock()
sensor.SensorDeviceClass.MONETARY = "monetary"
sensor.SensorStateClass = MagicMock()
sensor.SensorStateClass.TOTAL = "total"
sensor.SensorStateClass.TOTAL_INCREASING = "total_increasing"
sensor.SensorStateClass.MEASUREMENT = "measurement"

update_coordinator.CoordinatorEntity = MockCoordinatorEntity
update_coordinator.DataUpdateCoordinator = MockDataUpdateCoordinator
update_coordinator.UpdateFailed = MockUpdateFailed
