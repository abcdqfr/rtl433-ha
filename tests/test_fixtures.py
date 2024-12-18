"""Test fixtures for RTL-433 integration tests."""
import asyncio
import json
import logging
from typing import AsyncGenerator, Dict, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

_LOGGER = logging.getLogger(__name__)

class RTL433ProcessMock:
    """Mock RTL-433 process with debugging capabilities."""

    def __init__(self):
        """Initialize RTL-433 process mock."""
        self.stdout = AsyncMock()
        self.stderr = AsyncMock()
        self.returncode = None
        self.debug_info = {
            "command_history": [],
            "data_sent": [],
            "errors_generated": []
        }
        self._stdout_data = b""
        self._stderr_data = b""
        self._configure_communicate()

    def _configure_communicate(self) -> None:
        """Configure communicate method."""
        async def _communicate():
            self.debug_info["command_history"].append("communicate")
            return self._stdout_data, self._stderr_data
        self.communicate = _communicate

    def configure_normal_operation(self) -> None:
        """Configure mock for normal operation."""
        self.returncode = 0
        self._stdout_data = json.dumps({
            "model": "Acurite-Tower",
            "id": 1234,
            "temperature_C": 22.5,
            "humidity": 45,
            "battery_ok": 1,
            "channel": "A"
        }).encode() + b"\n"
        self._stderr_data = b""
        self.debug_info["command_history"].append("configure_normal_operation")
        self._configure_communicate()

    def configure_error_scenario(self, scenario: str) -> None:
        """Configure mock for various error scenarios."""
        scenarios = {
            "device_busy": (b"", b"usb_claim_interface error", 1),
            "device_not_found": (b"", b"not found", 1),
            "invalid_json": (b"invalid json data\n", b"", 0),
            "timeout": (b"", b"", -1),
        }
        
        stdout, stderr, return_code = scenarios.get(scenario, (b"", b"unknown error", 1))
        self._stdout_data = stdout
        self._stderr_data = stderr
        self.returncode = return_code
        self.debug_info["errors_generated"].append({
            "scenario": scenario,
            "stdout": stdout,
            "stderr": stderr,
            "return_code": return_code
        })
        self._configure_communicate()

    async def wait(self) -> int:
        """Wait for process to complete."""
        self.debug_info["command_history"].append("wait")
        return self.returncode

    async def terminate(self) -> None:
        """Terminate the process."""
        self.debug_info["command_history"].append("terminate")

    def get_debug_report(self) -> str:
        """Generate a debug report of mock's operation."""
        report = [
            "RTL-433 Process Mock Report:",
            f"Return Code: {self.returncode}",
            f"Commands Received: {len(self.debug_info['command_history'])}",
            f"Data Packets Sent: {len(self.debug_info['data_sent'])}",
            f"Errors Generated: {len(self.debug_info['errors_generated'])}"
        ]

        if self.debug_info["command_history"]:
            report.append("\nCommand History:")
            for cmd in self.debug_info["command_history"]:
                report.append(f"- {cmd}")

        if self.debug_info["errors_generated"]:
            report.append("\nErrors Generated:")
            for error in self.debug_info["errors_generated"]:
                report.append(f"- Scenario: {error['scenario']}")
                report.append(f"  Stdout: {error['stdout']}")
                report.append(f"  Stderr: {error['stderr']}")
                report.append(f"  Return Code: {error['return_code']}")

        return "\n".join(report)

@pytest.fixture
def mock_rtl433_data() -> Dict:
    """Provide mock RTL-433 sensor data with debugging info."""
    return {
        "model": "Acurite-Tower",
        "id": 1234,
        "temperature_C": 22.5,
        "humidity": 45,
        "battery_ok": 1,
        "channel": "A",
        "_debug": {
            "timestamp": "2024-01-01 00:00:00",
            "signal_strength": -75,
            "frequency_offset": 0.2,
            "raw_message": "Sample raw message"
        }
    }

@pytest.fixture
async def mock_coordinator(hass: HomeAssistant) -> AsyncGenerator:
    """Create a mock coordinator with debugging capabilities."""
    class DebugCoordinator:
        def __init__(self):
            self.data = {}
            self.last_update = None
            self.update_interval = 30
            self.update_errors = []
            self.debug_info = {
                "updates_requested": 0,
                "updates_successful": 0,
                "last_error": None,
                "device_stats": {}
            }

        async def async_refresh(self):
            """Refresh data with debug tracking."""
            self.debug_info["updates_requested"] += 1
            try:
                # Simulate data update
                await asyncio.sleep(0.1)
                self.debug_info["updates_successful"] += 1
            except Exception as err:
                self.debug_info["last_error"] = str(err)
                self.update_errors.append(err)
                raise

    coordinator = DebugCoordinator()
    yield coordinator

@pytest.fixture
def mock_add_entities() -> AddEntitiesCallback:
    """Mock add entities callback with debugging."""
    mock = MagicMock()
    mock.entities_added = []
    mock.side_effect = lambda entities, update=False: mock.entities_added.extend(entities)
    return mock

@pytest.fixture
async def mock_rtl433_process() -> AsyncGenerator:
    """Create a mock RTL-433 process with debugging capabilities."""
    process = RTL433ProcessMock()
    yield process

@pytest.fixture
def enable_debug_logging(caplog) -> None:
    """Enable debug logging for tests."""
    caplog.set_level(logging.DEBUG)
    _LOGGER.setLevel(logging.DEBUG)

@pytest.fixture
def mock_config_entry() -> Dict:
    """Create a mock config entry with debug options."""
    return {
        "device": "0",
        "frequency": "433.92M",
        "gain": 40,
        "protocol_filter": ["Acurite-Tower"],
        "debug_options": {
            "extended_logging": True,
            "save_raw_data": True,
            "device_timeout": 5,
            "retry_attempts": 3
        }
    } 