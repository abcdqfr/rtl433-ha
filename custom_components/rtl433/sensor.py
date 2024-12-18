"""Platform for RTL-433 sensor integration.

This module implements the sensor platform for RTL-433 devices, providing:
1. Dynamic sensor creation based on device model
2. State management and updates
3. Device registry integration
4. Sensor type configuration
"""
from __future__ import annotations

import logging
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

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up RTL-433 sensors from a config entry."""
    _LOGGER.debug("Setting up RTL-433 sensor platform for entry: %s", config_entry.entry_id)
    
    try:
        coordinator_data = hass.data[DOMAIN][config_entry.entry_id]
        coordinator: RTL433Coordinator = coordinator_data["coordinator"]
        _LOGGER.debug("Retrieved coordinator for entry %s", config_entry.entry_id)
    except KeyError as err:
        _LOGGER.error("Failed to get coordinator: %s. Data structure: %s", err, hass.data.get(DOMAIN, {}))
        return

    @callback
    def _async_process_data(coordinator_data: Dict[str, Any]) -> None:
        """Process coordinator data and create entities."""
        _LOGGER.debug("Processing coordinator data update: %s", coordinator_data)
        
        if not coordinator_data:
            _LOGGER.warning("Received empty coordinator data")
            return

        new_entities = []
        for device_id, device_data in coordinator_data.items():
            if device_id == "known_entities":
                continue
                
            _LOGGER.debug("Processing device data for %s: %s", device_id, device_data)
            
            # Extract device information from device_info
            device_info = device_data.get("device_info", {})
            model = device_info.get("model")
            if not model:
                _LOGGER.warning("Missing model in device info: %s", device_info)
                continue

            _LOGGER.info("Processing device: %s (model: %s)", device_id, model)
            
            # Get available sensor types for this device model
            available_sensors = DEVICE_SENSORS.get(model, [])
            if not available_sensors:
                _LOGGER.warning("No sensor types defined for model: %s", model)
                continue
                
            _LOGGER.debug("Available sensors for %s: %s", model, available_sensors)
            
            # Get actual sensor data
            sensor_data = device_data.get("sensor_data", {})
            _LOGGER.debug("Sensor data for %s: %s", device_id, sensor_data)
            
            # Create sensor entities for each available sensor type
            for sensor_type in available_sensors:
                if sensor_type in sensor_data:
                    entity_id = f"{device_id}_{sensor_type}"
                    if entity_id not in coordinator.data.get("known_entities", set()):
                        _LOGGER.info("Creating sensor entity - device: %s, type: %s", device_id, sensor_type)
                        try:
                            entity = RTL433Sensor(
                                coordinator=coordinator,
                                device_id=device_id,
                                sensor_type=sensor_type,
                                model=model,
                            )
                            new_entities.append(entity)
                            if "known_entities" not in coordinator.data:
                                coordinator.data["known_entities"] = set()
                            coordinator.data["known_entities"].add(entity_id)
                            _LOGGER.info("Successfully created sensor entity for %s - %s", device_id, sensor_type)
                        except Exception as err:
                            _LOGGER.error("Failed to create sensor entity for %s - %s: %s", device_id, sensor_type, err, exc_info=True)

        if new_entities:
            _LOGGER.info("Adding %d new sensor entities", len(new_entities))
            async_add_entities(new_entities)

    # Process any existing data
    if coordinator.data:
        _LOGGER.info("Processing existing devices: %s", list(coordinator.data.keys()))
        _async_process_data(coordinator.data)
    else:
        _LOGGER.info("No existing devices to process")


class RTL433Sensor(CoordinatorEntity[RTL433Coordinator], SensorEntity):
    """Representation of a RTL-433 sensor."""

    def __init__(
        self,
        coordinator: RTL433Coordinator,
        device_id: str,
        sensor_type: str,
        model: str,
    ) -> None:
        """Initialize the RTL-433 sensor."""
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
            
        _LOGGER.debug(
            "Initialized sensor - ID: %s, Type: %s, Name: %s",
            self._attr_unique_id,
            sensor_type,
            self._attr_name
        )

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        if self._device_id in self.coordinator.data:
            device_data = self.coordinator.data[self._device_id]
            if "sensor_data" in device_data:
                value = device_data["sensor_data"].get(self._sensor_type)
                
                # Format battery status
                if self._sensor_type == "battery_ok":
                    formatted_value = "OK" if value else "Low"
                    _LOGGER.debug("%s battery status: %s (raw: %s)", self._device_id, formatted_value, value)
                    return formatted_value
                    
                # Format signal quality
                if self._sensor_type in ["rssi", "snr", "noise"]:
                    if value is not None:
                        formatted_value = round(float(value), 1)
                        _LOGGER.debug("%s signal metric %s: %s", self._device_id, self._sensor_type, formatted_value)
                        return formatted_value
                
                _LOGGER.debug("%s %s value: %s", self._device_id, self._sensor_type, value)
                return value
                
        _LOGGER.debug("%s %s no value available", self._device_id, self._sensor_type)
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
                
            _LOGGER.debug("%s extra attributes: %s", self._device_id, attrs)
        
        return attrs

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        is_available = False
        if self._device_id in self.coordinator.data:
            device_data = self.coordinator.data[self._device_id]
            is_available = bool(device_data.get("sensor_data", {}).get(self._sensor_type) is not None)
        
        if not is_available:
            _LOGGER.debug("%s %s is unavailable", self._device_id, self._sensor_type)
            
        return is_available

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        if self._device_id in self.coordinator.data:
            return self.coordinator.data[self._device_id]["device_info"]
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=f"{self._model} {self._device_id.split('_')[-1]}",
            manufacturer="RTL-433",
            model=self._model,
            via_device=(DOMAIN, self.coordinator.device_id),
        ) 