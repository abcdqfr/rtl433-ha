"""RTL-433 coordinator for managing device state and data updates."""
from __future__ import annotations

import asyncio
import json
import logging
import subprocess
import os
from datetime import timedelta
from typing import Any, Dict, Optional, Set, Callable

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.entity import DeviceInfo, Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import (
    ATTR_BATTERY_LEVEL,
    ATTR_NAME,
    ATTR_MODEL,
    ATTR_MANUFACTURER,
)

from .const import (
    DOMAIN,
    CONF_DEVICE_ID,
    CONF_FREQUENCY,
    CONF_GAIN,
    CONF_PROTOCOL_FILTER,
    DEFAULT_FREQUENCY,
    DEFAULT_GAIN,
    DEVICE_SENSORS,
)

_LOGGER = logging.getLogger(__name__)

# Signal quality thresholds based on observed values
SIGNAL_EXCELLENT = -10  # dBm
SIGNAL_GOOD = -20      # dBm
SIGNAL_FAIR = -30      # dBm
SIGNAL_POOR = -40      # dBm

SNR_EXCELLENT = 30     # dB
SNR_GOOD = 20         # dB
SNR_FAIR = 10         # dB
SNR_POOR = 5          # dB

NOISE_EXCELLENT = -40  # dBm
NOISE_GOOD = -35      # dBm
NOISE_FAIR = -30      # dBm
NOISE_POOR = -25      # dBm

SUPPORTED_SENSOR_TYPES = {
    "temperature_C": ("Temperature", "°C"),
    "temperature_F": ("Temperature", "°F"),
    "humidity": ("Humidity", "%"),
    "battery_ok": ("Battery Status", None),
    "pressure_hPa": ("Pressure", "hPa"),
    "wind_speed_kph": ("Wind Speed", "km/h"),
    "wind_dir_deg": ("Wind Direction", "°"),
    "rain_mm": ("Rain", "mm"),
    "moisture": ("Moisture", "%"),
    "rssi": ("Signal Strength", "dBm"),
    "snr": ("Signal-to-Noise", "dB"),
    "noise": ("Noise Level", "dB"),
}

# Default protocols to enable if none specified
DEFAULT_PROTOCOLS = [1, 2, 3, 4, 8, 10, 11, 12, 18, 19, 20, 32, 34, 40, 41, 42, 47, 52, 54, 55, 73, 74, 75, 76]

class RTL433Coordinator(DataUpdateCoordinator):
    """Class to manage fetching RTL-433 data."""

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        device_id: str,
        frequency: str = DEFAULT_FREQUENCY,
        gain: int = DEFAULT_GAIN,
        protocol_filter: list[str] | None = None,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
        )
        self.hass = hass
        self.device_id = device_id
        self.frequency = frequency
        self.gain = gain
        self.protocol_filter = [int(p) for p in protocol_filter] if protocol_filter else DEFAULT_PROTOCOLS
        self._process: Optional[asyncio.subprocess.Process] = None
        self._shutdown = False
        self._retry_count = 0
        self._max_retries = 3
        self._retry_delay = 5  # seconds
        self._known_devices: Set[str] = set()
        self._device_init_attempts = 0
        self._max_device_init_attempts = 3
        self._device_init_delay = 2  # seconds
        self._add_entities_callback: Optional[AddEntitiesCallback] = None
        self._entity_cleanup_callbacks: Dict[str, Callable] = {}
        self._signal_quality_history: Dict[str, list] = {}
        self._last_device_update: Dict[str, str] = {}
        
        # Initialize data storage
        self.data: Dict[str, Dict[str, Any]] = {}
        self._pending_devices: Dict[str, Dict[str, Any]] = {}

    def register_add_entities_callback(self, callback: AddEntitiesCallback) -> None:
        """Register the callback to add entities."""
        self._add_entities_callback = callback
        # Process any pending devices
        if self._pending_devices and self._add_entities_callback:
            for device_id, device_data in self._pending_devices.items():
                if device_id not in self._known_devices:
                    self._process_new_device(device_id, device_data)
            self._pending_devices.clear()

    def _process_new_device(self, device_id: str, device_data: Dict[str, Any]) -> None:
        """Process a newly discovered device."""
        if not self._add_entities_callback:
            self._pending_devices[device_id] = device_data
            return

        model = device_data.get("model")
        if not model or model not in DEVICE_SENSORS:
            return

        self._known_devices.add(device_id)
        _LOGGER.info(
            "Processing new device - Model: %s, ID: %s, Available sensors: %s",
            model,
            device_id,
            ", ".join(DEVICE_SENSORS[model])
        )

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from RTL-433."""
        if self._shutdown:
            raise UpdateFailed("Coordinator is shutting down")

        try:
            return await self._fetch_rtl433_data()
        except Exception as err:
            self._retry_count += 1
            if self._retry_count >= self._max_retries:
                self._retry_count = 0
                raise UpdateFailed(f"Failed to fetch RTL-433 data after {self._max_retries} attempts: {err}")
            
            _LOGGER.warning(
                "Failed to fetch RTL-433 data (attempt %d/%d): %s",
                self._retry_count,
                self._max_retries,
                err,
            )
            await asyncio.sleep(self._retry_delay)
            return await self._async_update_data()

    async def _start_rtl433_process(self) -> None:
        """Start the RTL-433 process."""
        if self._process is not None:
            await self._cleanup_process()

        cmd = [
            "rtl_433",
            "-d", str(self.device_id),
            "-f", str(self.frequency),
            "-g", str(self.gain),
            "-F", "json",
            "-M", "level",    # Include signal level
            "-C", "si",       # Use SI units
            "-M", "time:iso", # ISO timestamp
            "-M", "protocol", # Include protocol info
            "-M", "stats",    # Include statistics
            "-v",            # Verbose output for debugging
        ]

        # Add protocol filters
        if self.protocol_filter:
            for protocol in self.protocol_filter:
                cmd.extend(["-R", str(protocol)])

        try:
            # First check if the device is available and reset it
            def _check_and_reset_device():
                try:
                    # Try to reset the device first
                    subprocess.run(
                        ["rtl_eeprom", "-d", str(self.device_id), "-t"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    # Then test it
                    return subprocess.run(
                        ["rtl_test", "-d", str(self.device_id), "-t"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                except subprocess.SubprocessError:
                    # If rtl_eeprom fails, try direct test
                    return subprocess.run(
                        ["rtl_test", "-d", str(self.device_id), "-t"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
            
            await self.hass.async_add_executor_job(_check_and_reset_device)
            
            # Start the RTL-433 process with a clean environment
            env = os.environ.copy()
            env["LANG"] = "C"  # Ensure consistent output format
            
            self._process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                limit=1024 * 1024,  # 1MB buffer
                env=env
            )
            
            _LOGGER.info("Started RTL-433 process with command: %s", " ".join(cmd))
            
            # Start monitoring tasks
            self.hass.loop.create_task(self._read_rtl433_output())
            self.hass.loop.create_task(self._monitor_process())

        except subprocess.TimeoutError:
            raise ConfigEntryNotReady("Timeout while checking RTL-SDR device")
        except (OSError, asyncio.SubprocessError) as err:
            self._process = None
            raise ConfigEntryNotReady(
                f"Failed to start RTL-433 process: {err}"
            ) from err

    def _evaluate_signal_quality(self, rssi: float, snr: float, noise: float) -> str:
        """Evaluate overall signal quality based on RSSI, SNR, and noise floor."""
        if (rssi >= SIGNAL_EXCELLENT and 
            snr >= SNR_EXCELLENT and 
            noise <= NOISE_EXCELLENT):
            return "excellent"
        elif (rssi >= SIGNAL_GOOD and 
              snr >= SNR_GOOD and 
              noise <= NOISE_GOOD):
            return "good"
        elif (rssi >= SIGNAL_FAIR and 
              snr >= SNR_FAIR and 
              noise <= NOISE_FAIR):
            return "fair"
        elif (rssi >= SIGNAL_POOR and 
              snr >= SNR_POOR and 
              noise <= NOISE_POOR):
            return "poor"
        return "unusable"

    def _track_signal_quality(self, device_id: str, quality: str) -> None:
        """Track signal quality history for a device."""
        if device_id not in self._signal_quality_history:
            self._signal_quality_history[device_id] = []
        
        history = self._signal_quality_history[device_id]
        history.append(quality)
        
        # Keep last 10 readings
        if len(history) > 10:
            history.pop(0)
        
        # Log if signal quality is consistently poor
        if len(history) >= 5 and all(q in ["poor", "unusable"] for q in history[-5:]):
            _LOGGER.warning(
                "Device %s has had poor signal quality for 5 consecutive readings",
                device_id
            )

    async def _monitor_process(self) -> None:
        """Monitor the RTL-433 process for errors."""
        if not self._process or not self._process.stderr:
            return

        while not self._shutdown:
            try:
                line = await self._process.stderr.readline()
                if not line:
                    if self._process.returncode is not None:
                        _LOGGER.warning("RTL-433 process ended with return code %d", self._process.returncode)
                        break
                    continue

                error_msg = line.decode().strip()
                if error_msg:
                    # Log all stderr messages at debug level
                    _LOGGER.debug("RTL-433 stderr: %s", error_msg)

                    # Check for actual critical error conditions
                    if any(msg in error_msg.lower() for msg in [
                        "usb_claim_interface error",
                        "device not found",
                        "device or resource busy",
                    ]):
                        _LOGGER.error("Critical RTL-433 error: %s", error_msg)
                        await self._handle_process_error()
                        break

            except Exception as err:
                _LOGGER.error("Error monitoring RTL-433 process: %s", err)
                break

        if not self._shutdown:
            await self._handle_process_error()

    async def _handle_process_error(self) -> None:
        """Handle process errors."""
        try:
            await self._cleanup_process()
            # Request a refresh which will restart the process
            await self.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Error during process error handling: %s", err)

    async def _fetch_rtl433_data(self) -> Dict[str, Any]:
        """Fetch data from RTL-433 process."""
        if self._process is None or self._process.returncode is not None:
            await self._initialize_rtl_device()
            await self._start_rtl433_process()

        return self.data

    async def _initialize_rtl_device(self) -> None:
        """Initialize the RTL-SDR device with retries."""
        while self._device_init_attempts < self._max_device_init_attempts:
            try:
                # First try to reset the USB device
                def _reset_usb():
                    try:
                        # Try rtl_eeprom reset first (most portable)
                        subprocess.run(
                            ["rtl_eeprom", "-d", str(self.device_id)],
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                    except subprocess.SubprocessError:
                        # If that fails, try to unload and reload the driver
                        subprocess.run(["rmmod", "rtl2832_sdr"], capture_output=True)
                        subprocess.run(["rmmod", "dvb_usb_rtl28xxu"], capture_output=True)
                        subprocess.run(["modprobe", "rtl2832_sdr"], capture_output=True)
                        subprocess.run(["modprobe", "dvb_usb_rtl28xxu"], capture_output=True)
                
                await self.hass.async_add_executor_job(_reset_usb)
                
                # Wait for device to settle
                await asyncio.sleep(self._device_init_delay)
                
                # Test device
                def _test_device():
                    return subprocess.run(
                        ["rtl_test", "-d", str(self.device_id), "-t"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                
                result = await self.hass.async_add_executor_job(_test_device)
                
                if "usb_claim_interface error" in result.stderr:
                    raise subprocess.CalledProcessError(1, "rtl_test", result.stdout, result.stderr)
                
                # PLL not locked is normal, don't treat it as an error
                _LOGGER.info("RTL-SDR device initialized successfully")
                self._device_init_attempts = 0  # Reset counter on success
                return
                
            except subprocess.CalledProcessError as err:
                self._device_init_attempts += 1
                _LOGGER.warning(
                    "Failed to initialize RTL-SDR device (attempt %d/%d): %s",
                    self._device_init_attempts,
                    self._max_device_init_attempts,
                    err,
                )
                if "usb_claim_interface error" in str(err):
                    _LOGGER.warning("USB interface claim error - device may be in use or have permission issues")
                await asyncio.sleep(self._device_init_delay)
                
        raise ConfigEntryNotReady(
            f"Failed to initialize RTL-SDR device after {self._max_device_init_attempts} attempts. "
            "Please check device permissions and ensure it's not in use by another application."
        )

    async def _read_rtl433_output(self) -> None:
        """Read and process output from RTL-433."""
        if not self._process or not self._process.stdout:
            return

        buffer = ""
        while not self._shutdown:
            try:
                chunk = await self._process.stdout.read(1024)
                if not chunk:
                    break

                buffer += chunk.decode()
                
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    try:
                        data = json.loads(line)
                        await self._process_device_data(data)
                        _LOGGER.debug("Received RTL-433 data: %s", data)
                    except json.JSONDecodeError:
                        _LOGGER.debug("Received invalid JSON from rtl_433: %s", line)
                    except Exception as err:
                        _LOGGER.error("Error processing RTL-433 data: %s", err)

            except Exception as err:
                _LOGGER.error("Error reading RTL-433 output: %s", err)
                break

        if not self._shutdown:
            _LOGGER.warning("RTL-433 process output stream ended")
            await self._handle_process_error()

    @callback
    async def _process_device_data(self, data: Dict[str, Any]) -> None:
        """Process received device data."""
        if not isinstance(data, dict):
            return

        # Extract core device information
        model = data.get("model")
        device_id = data.get("id")
        if not model or not device_id:
            return

        # Create unique device identifier
        unique_id = f"{model}_{device_id}"

        # Apply protocol filter if configured
        protocol = data.get("protocol")
        if self.protocol_filter and protocol is not None:
            if protocol not in self.protocol_filter:
                _LOGGER.debug(
                    "Filtered out device %s with protocol %s (not in %s)",
                    unique_id,
                    protocol,
                    self.protocol_filter
                )
                return

        # Evaluate signal quality
        rssi = float(data.get("rssi", 0))
        snr = float(data.get("snr", 0))
        noise = float(data.get("noise", 0))
        signal_quality = self._evaluate_signal_quality(rssi, snr, noise)
        
        # Track signal quality
        self._track_signal_quality(unique_id, signal_quality)

        # Format sensor data
        sensor_data = {
            key: self._format_sensor_value(key, value)
            for key, value in data.items()
            if key not in ["model", "id", "brand", "protocol"] and value is not None
        }

        # Add metadata
        device_info = {
            "identifiers": {(DOMAIN, unique_id)},
            "name": f"{model} Sensor {device_id}",
            "manufacturer": data.get("brand", "RTL-433"),
            "model": model,
            "via_device": (DOMAIN, self.device_id),
        }

        # Update device data
        self.data[unique_id] = {
            "device_info": device_info,
            "sensor_data": sensor_data,
            "last_update": data.get("time", ""),
            "signal_quality": {
                "rssi": rssi,
                "snr": snr,
                "noise": noise,
                "quality": signal_quality,
            }
        }

        # Process new device if needed
        if unique_id not in self._known_devices:
            self._process_new_device(unique_id, data)
            _LOGGER.info(
                "Discovered new device - Model: %s, ID: %s, Protocol: %s, Signal: %s, Sensors: %s",
                model,
                device_id,
                protocol,
                signal_quality,
                ", ".join(sensor_data.keys()),
            )

        # Update coordinator data
        self.async_set_updated_data(self.data)
        _LOGGER.debug("Processing device data: %s", data)

    def _format_sensor_value(self, key: str, value: Any) -> Any:
        """Format sensor values consistently."""
        if isinstance(value, (int, float)):
            # Round floating point values to 2 decimal places
            return round(float(value), 2)
        elif key == "battery_ok":
            return bool(value)
        return value

    async def _cleanup_process(self) -> None:
        """Clean up the RTL-433 process."""
        if self._process is None:
            return

        try:
            if self._process.returncode is None:
                self._process.terminate()
                try:
                    await asyncio.wait_for(self._process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    _LOGGER.warning("RTL-433 process did not terminate, killing it")
                    self._process.kill()
                    await self._process.wait()
        except Exception as err:
            _LOGGER.error("Error cleaning up RTL-433 process: %s", err)
        finally:
            self._process = None

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator."""
        self._shutdown = True
        await self._cleanup_process()
        await super().async_shutdown()

class RTL433Sensor(Entity):
    """Representation of a RTL-433 sensor."""

    def __init__(self, coordinator, unique_id, name, device_info):
        """Initialize the sensor."""
        self.coordinator = coordinator
        self.unique_id = unique_id
        self._name = name
        self._device_info = device_info

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def unique_id(self):
        """Return a unique ID for this sensor."""
        return self.unique_id

    @property
    def device_info(self):
        """Return device information."""
        return self._device_info

    @property
    def state(self):
        """Return the state of the sensor."""
        return self.coordinator.data[self.unique_id]["sensor_data"]

    async def async_update(self):
        """Fetch new state data for the sensor."""
        await self.coordinator.async_request_refresh()