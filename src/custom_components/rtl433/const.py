"""Constants for the RTL-433 integration.

This module defines all constants used throughout the RTL-433 integration:
1. Configuration constants and defaults
2. Device models and capabilities
3. Sensor type definitions and units
4. Error messages and event names

The constants are organized by category and include type hints and
documentation for improved maintainability.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Set, TypedDict, Union

from homeassistant.const import (
    UnitOfTemperature,
    PERCENTAGE,
    DEGREE,
    UnitOfLength,
    UnitOfSpeed,
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)

# Integration domain
DOMAIN: str = "rtl433"

#
# Configuration Constants
#
CONF_DEVICE_ID: str = "device_id"
CONF_FREQUENCY: str = "frequency"
CONF_GAIN: str = "gain"
CONF_PROTOCOL_FILTER: str = "protocol_filter"

# Default configuration values
DEFAULT_FREQUENCY: str = "433.92M"
DEFAULT_GAIN: int = 40
DEFAULT_DEVICE_ID: str = "0"

#
# Event Names
#
EVENT_DEVICE_MESSAGE: str = "rtl433_device_message"

#
# Error Messages
#
ERROR_PROCESS_FAILED: str = "RTL-433 process failed to start"
ERROR_DEVICE_NOT_FOUND: str = "RTL-SDR device not found"
ERROR_PROCESS_CRASHED: str = "RTL-433 process crashed"
ERROR_INVALID_PROTOCOL: str = "Invalid protocol specified"
ERROR_INVALID_SENSOR_VALUE: str = "Invalid sensor value received"

#
# Protocol Validation
#
VALID_PROTOCOLS: Set[str] = {
    "Acurite-5n1",
    "Acurite-Tower",
    "LaCrosse-TX141W",
    "Oregon-v1",
    "Ambient-Weather",
    "Fine-Offset",
    "Nexus-TH",
    "Prologue-TH",
    "Rubicson-Temperature",
    "WT450",
}

# Protocol-specific value ranges
class ValueRange(TypedDict):
    """Type definition for sensor value range."""
    min: float
    max: float
    step: Optional[float]

class ProtocolLimits(TypedDict):
    """Type definition for protocol-specific value limits."""
    temperature_C: ValueRange
    temperature_F: ValueRange
    humidity: ValueRange
    wind_avg_km_h: ValueRange
    wind_dir_deg: ValueRange
    rain_in: ValueRange

PROTOCOL_LIMITS: Dict[str, ProtocolLimits] = {
    "Acurite-5n1": {
        "temperature_F": {"min": -40, "max": 158, "step": 0.1},
        "humidity": {"min": 0, "max": 100, "step": 1},
        "wind_avg_km_h": {"min": 0, "max": 160, "step": 0.1},
        "wind_dir_deg": {"min": 0, "max": 360, "step": 1},
        "rain_in": {"min": 0, "max": 100, "step": 0.01},
    },
    "LaCrosse-TX141W": {
        "temperature_C": {"min": -40, "max": 60, "step": 0.1},
        "humidity": {"min": 0, "max": 100, "step": 1},
        "wind_avg_km_h": {"min": 0, "max": 160, "step": 0.1},
        "wind_dir_deg": {"min": 0, "max": 360, "step": 1},
    },
}

# Common value ranges
COMMON_RANGES: Dict[str, ValueRange] = {
    "temperature_C": {"min": -40, "max": 80, "step": 0.1},
    "temperature_F": {"min": -40, "max": 176, "step": 0.1},
    "humidity": {"min": 0, "max": 100, "step": 1},
    "wind_avg_km_h": {"min": 0, "max": 200, "step": 0.1},
    "wind_dir_deg": {"min": 0, "max": 360, "step": 1},
    "rain_in": {"min": 0, "max": 100, "step": 0.01},
}

#
# Device Models
#
MODEL_ACURITE_5N1: str = "Acurite-5n1"
MODEL_LACROSSE_TX141W: str = "LaCrosse-TX141W"

#
# Sensor Type Definitions
#
class SensorTypeInfo(TypedDict):
    """Type definition for sensor information."""
    device_class: Optional[str]
    state_class: str
    unit: Optional[str]
    icon: str

SENSOR_TYPES: Dict[str, SensorTypeInfo] = {
    "temperature_C": {
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "°C",
        "icon": "mdi:thermometer",
    },
    "temperature_F": {
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "°F",
        "icon": "mdi:thermometer",
    },
    "humidity": {
        "device_class": SensorDeviceClass.HUMIDITY,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "%",
        "icon": "mdi:water-percent",
    },
    "battery_ok": {
        "device_class": SensorDeviceClass.BATTERY,
        "state_class": None,
        "unit": None,
        "icon": "mdi:battery",
    },
    "pressure_hPa": {
        "device_class": SensorDeviceClass.PRESSURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "hPa",
        "icon": "mdi:gauge",
    },
    "wind_speed_kph": {
        "device_class": SensorDeviceClass.WIND_SPEED,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "km/h",
        "icon": "mdi:weather-windy",
    },
    "wind_dir_deg": {
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "°",
        "icon": "mdi:compass",
    },
    "rain_mm": {
        "device_class": SensorDeviceClass.PRECIPITATION,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": "mm",
        "icon": "mdi:water",
    },
    "moisture": {
        "device_class": SensorDeviceClass.MOISTURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "%",
        "icon": "mdi:water-percent",
    },
    "rssi": {
        "device_class": SensorDeviceClass.SIGNAL_STRENGTH,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "dBm",
        "icon": "mdi:signal",
    },
    "snr": {
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "dB",
        "icon": "mdi:signal-variant",
    },
    "noise": {
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "dB",
        "icon": "mdi:volume-high",
    },
}

#
# Device Capabilities
#
DEVICE_SENSORS: Dict[str, List[str]] = {
    MODEL_ACURITE_5N1: [
        "temperature_C",
        "humidity",
        "wind_speed_kph",
        "wind_dir_deg",
        "rain_mm",
        "battery_ok",
        "rssi",
        "snr",
        "noise",
    ],
    MODEL_LACROSSE_TX141W: [
        "temperature_C",
        "humidity",
        "battery_ok",
        "rssi",
        "snr",
        "noise",
    ],
} 