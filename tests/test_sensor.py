"""Test the RTL-433 sensor platform."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from homeassistant.core import HomeAssistant
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import CONF_DEVICE_ID
from custom_components.rtl433.sensor import async_setup_entry
from custom_components.rtl433.const import DOMAIN
from custom_components.rtl433.coordinator import RTL433Coordinator

@pytest.fixture
def mock_coordinator(hass):
    """Create a mock coordinator."""
    coordinator = RTL433Coordinator(hass, "test_entry", {
        "device": "0",
        "frequency": "433.92M",
        "gain": 40,
    })
    coordinator.data = {
        "Acurite-Tower_1234": {
            "model": "Acurite-Tower",
            "id": 1234,
            "temperature_C": 22.5,
            "humidity": 45,
            "battery_ok": 1,
            "channel": "A"
        }
    }
    return coordinator

@pytest.mark.asyncio
async def test_sensor_setup(hass: HomeAssistant, config_entry, mock_coordinator):
    """Test sensor setup."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config_entry.entry_id] = {
        "coordinator": mock_coordinator
    }
    
    async_add_entities = AsyncMock()
    await async_setup_entry(hass, config_entry, async_add_entities)
    
    # Verify entities were added
    assert async_add_entities.call_count == 1
    entities = async_add_entities.call_args[0][0]
    assert len(entities) > 0

@pytest.mark.asyncio
async def test_sensor_state(hass: HomeAssistant, config_entry, mock_coordinator):
    """Test sensor state."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config_entry.entry_id] = {
        "coordinator": mock_coordinator
    }
    
    async_add_entities = AsyncMock()
    await async_setup_entry(hass, config_entry, async_add_entities)
    
    entities = async_add_entities.call_args[0][0]
    temp_sensor = next(e for e in entities if e._sensor_type == "temperature_C")
    humidity_sensor = next(e for e in entities if e._sensor_type == "humidity")
    battery_sensor = next(e for e in entities if e._sensor_type == "battery_ok")
    
    # Test temperature sensor
    assert temp_sensor.native_value == 22.5
    assert temp_sensor.device_class == SensorDeviceClass.TEMPERATURE
    assert temp_sensor.state_class == SensorStateClass.MEASUREMENT
    
    # Test humidity sensor
    assert humidity_sensor.native_value == 45
    assert humidity_sensor.device_class == SensorDeviceClass.HUMIDITY
    assert humidity_sensor.state_class == SensorStateClass.MEASUREMENT
    
    # Test battery sensor
    assert battery_sensor.native_value == "OK"
    assert battery_sensor.entity_category == "diagnostic"

@pytest.mark.asyncio
async def test_sensor_device_info(hass: HomeAssistant, config_entry, mock_coordinator):
    """Test sensor device info."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config_entry.entry_id] = {
        "coordinator": mock_coordinator
    }
    
    async_add_entities = AsyncMock()
    await async_setup_entry(hass, config_entry, async_add_entities)
    
    entities = async_add_entities.call_args[0][0]
    sensor = entities[0]
    
    device_info = sensor.device_info
    assert device_info["identifiers"] == {(DOMAIN, "Acurite-Tower_1234")}
    assert device_info["name"] == "Acurite-Tower Acurite-Tower_1234"
    assert device_info["manufacturer"] == "RTL-433"
    assert device_info["model"] == "Acurite-Tower"
    assert device_info["via_device"] == (DOMAIN, "0")

@pytest.mark.asyncio
async def test_sensor_update(hass: HomeAssistant, config_entry, mock_coordinator):
    """Test sensor update."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config_entry.entry_id] = {
        "coordinator": mock_coordinator
    }
    
    async_add_entities = AsyncMock()
    await async_setup_entry(hass, config_entry, async_add_entities)
    
    entities = async_add_entities.call_args[0][0]
    temp_sensor = next(e for e in entities if e._sensor_type == "temperature_C")
    
    # Update coordinator data
    mock_coordinator.data = {
        "Acurite-Tower_1234": {
            "model": "Acurite-Tower",
            "id": 1234,
            "temperature_C": 23.5,
            "humidity": 46,
            "battery_ok": 1,
            "channel": "A"
        }
    }
    mock_coordinator.async_set_updated_data(mock_coordinator.data)
    
    # Verify sensor state updated
    assert temp_sensor.native_value == 23.5