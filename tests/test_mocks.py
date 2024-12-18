"""Test mocks for RTL-433 integration tests."""
import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

_LOGGER = logging.getLogger(__name__)

class DebugAsyncMock(AsyncMock):
    """AsyncMock with debugging capabilities."""

    def __init__(self, *args, **kwargs):
        """Initialize debug async mock."""
        super().__init__(*args, **kwargs)
        self.call_history: List[Dict[str, Any]] = []
        self.error_history: List[Dict[str, Any]] = []

    async def __call__(self, *args, **kwargs):
        """Track mock calls with debug info."""
        call_info = {
            "args": args,
            "kwargs": kwargs,
            "call_count": self.call_count + 1
        }
        self.call_history.append(call_info)
        
        try:
            result = await super().__call__(*args, **kwargs)
            call_info["result"] = result
            return result
        except Exception as err:
            error_info = {
                "error": str(err),
                "call_info": call_info
            }
            self.error_history.append(error_info)
            raise

class RTL433ProcessMock:
    """Mock RTL-433 process with debugging capabilities."""

    def __init__(self, device_id: str = "0"):
        """Initialize RTL-433 process mock."""
        self.device_id = device_id
        self.stdout = DebugAsyncMock()
        self.stderr = DebugAsyncMock()
        self.returncode: Optional[int] = None
        self.debug_data = {
            "command_history": [],
            "data_sent": [],
            "errors_generated": []
        }

    def configure_normal_operation(self) -> None:
        """Configure mock for normal operation."""
        self.stdout.readline.side_effect = self._generate_sample_data()
        self.stderr.read.return_value = b""
        self.returncode = 0

    def configure_error_scenario(self, scenario: str) -> None:
        """Configure mock for various error scenarios."""
        scenarios = {
            "device_busy": (b"usb_claim_interface error", 1),
            "device_not_found": (b"not found", 1),
            "invalid_json": (b"invalid data", 0),
            "timeout": (b"", -1),
        }
        
        error_output, return_code = scenarios.get(scenario, (b"unknown error", 1))
        self.stderr.read.return_value = error_output
        self.returncode = return_code
        self.debug_data["errors_generated"].append({
            "scenario": scenario,
            "output": error_output,
            "return_code": return_code
        })

    def _generate_sample_data(self):
        """Generate sample RTL-433 data with debugging info."""
        sample_data = [
            {
                "model": "Acurite-Tower",
                "id": 1234,
                "temperature_C": 22.5,
                "humidity": 45,
                "battery_ok": 1,
                "channel": "A",
                "_debug": {
                    "timestamp": "2024-01-01 00:00:00",
                    "signal_strength": -75
                }
            },
            {
                "model": "Oregon-THN128",
                "id": 5678,
                "temperature_C": 23.0,
                "battery": 1,
                "_debug": {
                    "timestamp": "2024-01-01 00:00:01",
                    "signal_strength": -80
                }
            }
        ]

        async def generate():
            for data in sample_data:
                json_data = json.dumps(data).encode() + b"\n"
                self.debug_data["data_sent"].append(data)
                yield json_data

        return generate().__aiter__().__anext__

    def get_debug_report(self) -> str:
        """Generate a debug report of mock's operation."""
        report = [
            "RTL-433 Process Mock Report:",
            f"Device ID: {self.device_id}",
            f"Return Code: {self.returncode}",
            f"Commands Received: {len(self.debug_data['command_history'])}",
            f"Data Packets Sent: {len(self.debug_data['data_sent'])}",
            f"Errors Generated: {len(self.debug_data['errors_generated'])}"
        ]

        if self.debug_data["command_history"]:
            report.append("\nCommand History:")
            for cmd in self.debug_data["command_history"]:
                report.append(f"- {cmd}")

        if self.debug_data["errors_generated"]:
            report.append("\nErrors Generated:")
            for error in self.debug_data["errors_generated"]:
                report.append(f"- Scenario: {error['scenario']}")
                report.append(f"  Output: {error['output']}")
                report.append(f"  Return Code: {error['return_code']}")

        return "\n".join(report)

class HomeAssistantMock:
    """Mock Home Assistant with debugging capabilities."""

    def __init__(self):
        """Initialize Home Assistant mock."""
        self.states = {}
        self.services = {}
        self.config = MagicMock()
        self.bus = MagicMock()
        self.debug_info = {
            "state_changes": [],
            "service_calls": [],
            "events_fired": []
        }

    async def async_add_job(self, target, *args):
        """Add a job to Home Assistant with debug tracking."""
        try:
            if asyncio.iscoroutinefunction(target):
                await target(*args)
            else:
                target(*args)
        except Exception as err:
            _LOGGER.error("Error in async_add_job: %s", str(err))
            raise

    def async_create_task(self, target):
        """Create a task with debug tracking."""
        task = asyncio.create_task(target)
        return task

    def get_debug_report(self) -> str:
        """Generate a debug report of Home Assistant mock's operation."""
        report = [
            "Home Assistant Mock Report:",
            f"State Changes: {len(self.debug_info['state_changes'])}",
            f"Service Calls: {len(self.debug_info['service_calls'])}",
            f"Events Fired: {len(self.debug_info['events_fired'])}"
        ]

        if self.debug_info["state_changes"]:
            report.append("\nState Changes:")
            for change in self.debug_info["state_changes"]:
                report.append(f"- Entity: {change['entity_id']}")
                report.append(f"  Old: {change['old_state']}")
                report.append(f"  New: {change['new_state']}")

        if self.debug_info["service_calls"]:
            report.append("\nService Calls:")
            for call in self.debug_info["service_calls"]:
                report.append(f"- Service: {call['service']}")
                report.append(f"  Data: {call['data']}")

        return "\n".join(report) 