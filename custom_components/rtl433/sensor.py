"""Platform for RTL-433 sensor integration.

This module implements the sensor platform for RTL-433 devices, providing:
1. Dynamic sensor creation based on device model
2. State management and updates
3. Device registry integration
4. Sensor type configuration
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)
from homeassistant.helpers.entity import DeviceInfo

from .const import (
    DOMAIN,
    SENSOR_TYPES,
    DEVICE_SENSORS,
)
from .coordinator import RTL433Coordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up RTL-433 sensors from a config entry.
    
    This function:
    1. Initializes or retrieves the RTL-433 coordinator
    2. Sets up entity addition callback
    3. Creates sensors for existing devices
    4. Registers listener for new devices
    
    Args:
        hass: The Home Assistant instance
        config_entry: Configuration entry containing RTL-433 settings
        async_add_entities: Callback to register new entities
    """
    coordinator: RTL433Coordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    # Register the add_entities callback with the coordinator
    coordinator.register_add_entities_callback(async_add_entities)

    @callback
    def _async_add_sensor(data: Dict[str, Any]) -> None:
        """Create and add sensors from RTL-433 data.
        
        Args:
            data: Device data containing model, id, and sensor readings
            
        The function:
        1. Validates device model
        2. Creates unique device identifier
        3. Creates sensors based on device capabilities
        4. Registers new entities with Home Assistant
        """
        if not isinstance(data, dict):
            return

        entities = []
        
        # Extract device information
        model = data.get("model")
        device_id = data.get("id")
        if not model or not device_id:
            return

        # Create unique device identifier
        unique_id = f"{model}_{device_id}"
        
        # Get available sensor types for this device model
        available_sensors = DEVICE_SENSORS.get(model, [])
        
        # Create sensor entities for each available sensor type
        for sensor_type in available_sensors:
            if sensor_type in data.get("sensor_data", {}):
                entities.append(
                    RTL433Sensor(
                        coordinator=coordinator,
                        device_id=unique_id,
                        sensor_type=sensor_type,
                        model=model,
                    )
                )

        if entities:
            async_add_entities(entities)

    # Add sensors for existing devices
    if coordinator.data:
        for device_id, device_data in coordinator.data.items():
            _async_add_sensor(device_data)

    # Register callback for new devices
    coordinator.async_add_listener(
        lambda: _async_add_sensor(coordinator.data)
    )


class RTL433Sensor(CoordinatorEntity[RTL433Coordinator], SensorEntity):
    """Representation of a RTL-433 sensor.
    
    This class implements a Home Assistant sensor entity that:
    1. Receives updates from the RTL-433 coordinator
    2. Provides device registry information
    3. Handles state updates and attribute management
    4. Supports various sensor types (temperature, humidity, etc.)
    """

    def __init__(
        self,
        coordinator: RTL433Coordinator,
        device_id: str,
        sensor_type: str,
        model: str,
    ) -> None:
        """Initialize the RTL-433 sensor.
        
        Args:
            coordinator: The RTL-433 data coordinator
            device_id: Unique identifier for the device
            sensor_type: Type of sensor (temperature, humidity, etc.)
            model: Device model name
        """
        super().__init__(coordinator)
        
        self._device_id = device_id
        self._sensor_type = sensor_type
        self._model = model
        
        # Set entity attributes
        self._attr_unique_id = f"{device_id}_{sensor_type}"
        self._attr_name = f"{model} {sensor_type.replace('_', ' ').title()}"
        
        # Set sensor characteristics from SENSOR_TYPES
        sensor_info = SENSOR_TYPES[sensor_type]
        self._attr_device_class = sensor_info["device_class"]
        self._attr_state_class = sensor_info["state_class"]
        self._attr_native_unit_of_measurement = sensor_info["unit"]
        self._attr_icon = sensor_info["icon"]
        
        # Set diagnostic category for battery and signal sensors
        if sensor_type in ["battery_ok", "rssi", "snr", "noise"]:
            self._attr_entity_category = "diagnostic"

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        if self._device_id in self.coordinator.data:
            device_data = self.coordinator.data[self._device_id]
            if "sensor_data" in device_data:
                value = device_data["sensor_data"].get(self._sensor_type)
                
                # Format battery status
                if self._sensor_type == "battery_ok":
                    return "OK" if value else "Low"
                    
                # Format signal quality
                if self._sensor_type in ["rssi", "snr", "noise"]:
                    if value is not None:
                        return round(float(value), 1)
                
                return value
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        attrs = {}
        
        if self._device_id in self.coordinator.data:
            device_data = self.coordinator.data[self._device_id]
            
            # Add signal quality information
            if "signal_quality" in device_data:
                signal_quality = device_data["signal_quality"]
                attrs["signal_quality"] = signal_quality.get("quality", "unknown")
                
                if self._sensor_type in ["rssi", "snr", "noise"]:
                    attrs["raw_value"] = signal_quality.get(self._sensor_type)
            
            # Add last update time
            if "last_update" in device_data:
                attrs["last_update"] = device_data["last_update"]
        
        return attrs

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if self._device_id in self.coordinator.data:
            device_data = self.coordinator.data[self._device_id]
            return bool(device_data.get("sensor_data", {}).get(self._sensor_type) is not None)
        return False

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=f"{self._model} {self._device_id.split('_')[-1]}",
            manufacturer="RTL-433",
            model=self._model,
            via_device=(DOMAIN, self.coordinator.device_id),
        ) 