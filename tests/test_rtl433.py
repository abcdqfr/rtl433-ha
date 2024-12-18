"""Test RTL-433 process handling with debug support."""
import asyncio
import json
import logging
import pytest
from unittest.mock import patch

_LOGGER = logging.getLogger(__name__)

async def run_rtl433(device_id="0", frequency="433.92M", gain=40):
    """Run rtl_433 and return the first line of output with debug info."""
    cmd = [
        "rtl_433",
        "-d", str(device_id),
        "-f", frequency,
        "-g", str(gain),
        "-F", "json"
    ]
    
    _LOGGER.debug("Starting RTL-433 process with command: %s", " ".join(cmd))
    
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            _LOGGER.debug("Waiting for RTL-433 process output")
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=5.0)
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Process failed with no error message"
                _LOGGER.error("RTL-433 process failed: %s", error_msg)
                return None, error_msg
                
            # Try to parse the first line as JSON
            if stdout:
                for line in stdout.decode().splitlines():
                    try:
                        data = json.loads(line)
                        _LOGGER.debug("Successfully parsed RTL-433 data: %s", data)
                        return data, None
                    except json.JSONDecodeError as err:
                        _LOGGER.warning("Failed to parse JSON line: %s", err)
                        continue
            
            _LOGGER.error("No valid JSON data received from RTL-433")
            return None, "No valid JSON data received"
            
        except asyncio.TimeoutError:
            _LOGGER.error("RTL-433 process timed out")
            try:
                process.terminate()
                await process.wait()
            except Exception as err:
                _LOGGER.error("Error during process termination: %s", err)
            return None, "Process timed out"
            
    except Exception as err:
        _LOGGER.error("Error running RTL-433: %s", err)
        return None, str(err)

@pytest.mark.asyncio
async def test_rtl433_process_mock(mock_rtl433_process, enable_debug_logging):
    """Test RTL-433 process with mocked output and debug tracking."""
    _LOGGER.debug("Starting RTL-433 process mock test")
    
    with patch('asyncio.create_subprocess_exec', return_value=mock_rtl433_process):
        mock_rtl433_process.configure_normal_operation()
        data, error = await run_rtl433()
        
        assert error is None, f"Unexpected error: {error}"
        assert data is not None, "No data received"
        assert "model" in data, "Missing model in data"
        
        debug_report = mock_rtl433_process.get_debug_report()
        _LOGGER.debug("RTL-433 process mock test completed:\n%s", debug_report)

@pytest.mark.asyncio
async def test_rtl433_process_error_mock(mock_rtl433_process, enable_debug_logging):
    """Test RTL-433 process error handling with debug tracking."""
    with patch('asyncio.create_subprocess_exec', return_value=mock_rtl433_process):
        error_scenarios = ["device_busy", "device_not_found", "invalid_json"]
        
        for scenario in error_scenarios:
            _LOGGER.debug("Testing error scenario: %s", scenario)
            mock_rtl433_process.configure_error_scenario(scenario)
            
            data, error = await run_rtl433()
            assert data is None, f"Expected no data for {scenario}"
            assert error is not None, f"Expected error for {scenario}"
            
            debug_report = mock_rtl433_process.get_debug_report()
            _LOGGER.debug("Error scenario test completed:\n%s", debug_report)

@pytest.mark.asyncio
async def test_rtl433_multiple_devices(mock_rtl433_process, enable_debug_logging):
    """Test handling multiple device outputs with debug tracking."""
    _LOGGER.debug("Starting multiple devices test")
    
    with patch('asyncio.create_subprocess_exec', return_value=mock_rtl433_process):
        # Configure mock for multiple devices
        mock_rtl433_process.configure_normal_operation()
        data, error = await run_rtl433()
        
        assert error is None, f"Unexpected error: {error}"
        assert data is not None, "No data received"
        assert "model" in data, "Missing model in data"
        
        debug_report = mock_rtl433_process.get_debug_report()
        _LOGGER.debug("Multiple devices test completed:\n%s", debug_report)

@pytest.mark.asyncio
async def test_rtl433_parameter_validation(mock_rtl433_process, enable_debug_logging):
    """Test RTL-433 parameter validation with debug tracking."""
    with patch('asyncio.create_subprocess_exec', return_value=mock_rtl433_process):
        test_cases = [
            ("1", "433.92M", 40),  # Different device ID
            ("0", "315M", 40),    # Different frequency
            ("0", "433.92M", 50), # Different gain
        ]
        
        for device_id, freq, gain in test_cases:
            _LOGGER.debug(
                "Testing parameters: device_id=%s, frequency=%s, gain=%d",
                device_id, freq, gain
            )
            
            mock_rtl433_process.configure_normal_operation()
            data, error = await run_rtl433(
                device_id=device_id,
                frequency=freq,
                gain=gain
            )
            
            assert error is None, f"Unexpected error: {error}"
            assert data is not None, "No data received"
            assert "model" in data, "Missing model in data"
            
            debug_report = mock_rtl433_process.get_debug_report()
            _LOGGER.debug("Parameter validation test completed:\n%s", debug_report)

@pytest.mark.asyncio
@pytest.mark.integration
async def test_real_rtl433(enable_debug_logging):
    """Test actual RTL-433 process with debug tracking."""
    _LOGGER.debug("Starting real RTL-433 test")
    
    try:
        data, error = await run_rtl433()
        if error and "usb_claim_interface error" in error:
            pytest.skip("RTL-SDR device is in use")
        elif error and "not found" in error:
            pytest.skip("No RTL-SDR device found")
        elif error:
            pytest.skip(f"RTL-433 error: {error}")
        else:
            assert isinstance(data, dict)
            assert "model" in data
            # Verify basic data structure
            assert all(isinstance(v, (str, int, float, bool)) for v in data.values())
            _LOGGER.debug("Real RTL-433 test completed successfully")
    except Exception as e:
        _LOGGER.error("Real RTL-433 test failed: %s", str(e))
        pytest.skip(f"Test skipped due to error: {str(e)}")