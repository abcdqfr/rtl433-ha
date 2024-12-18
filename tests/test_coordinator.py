"""Test suite for the RTL-433 coordinator.

This module contains comprehensive tests for the RTL433Coordinator class,
covering process management, data processing, error handling, and cleanup operations.
"""
from __future__ import annotations

import asyncio
from typing import Any, AsyncGenerator, Dict, List, Tuple
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from _pytest.logging import LogCaptureFixture
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.exceptions import ConfigEntryNotReady

from custom_components.rtl433.coordinator import RTL433Coordinator
from custom_components.rtl433.const import DOMAIN

import time

async def wait_for_cleanup() -> None:
    """Wait for cleanup operations to complete.
    
    This helper function adds a small delay to ensure async cleanup
    operations have time to complete before assertions.
    """
    await asyncio.sleep(0.1)

# Test configuration with protocol filter
TEST_CONFIG: Dict[str, Any] = {
    "device": "0",
    "frequency": "433.92M",
    "gain": 40,
    "protocol_filter": ["Acurite-Tower"],
}

@pytest.fixture
def test_config() -> Dict[str, Any]:
    """Provide a test configuration with test mode enabled.
    
    Returns:
        Dict[str, Any]: Configuration dictionary for testing
    """
    return {
        "device": "0",
        "frequency": "433.92M",
        "gain": 40,
        "protocol_filter": [],
        "test_mode": True,  # Enable test mode for special handling
    }

@pytest.fixture
async def coordinator(hass: HomeAssistant, test_config: Dict[str, Any]) -> AsyncGenerator[RTL433Coordinator, None]:
    """Create and yield a test coordinator instance.
    
    This fixture handles proper cleanup of the coordinator and any
    remaining tasks after tests complete.
    
    Args:
        hass: HomeAssistant instance
        test_config: Test configuration dictionary
        
    Yields:
        RTL433Coordinator: Configured coordinator instance for testing
    """
    coordinator = RTL433Coordinator(hass, "test_entry", test_config)
    yield coordinator
    
    # Ensure proper cleanup
    await coordinator.shutdown()
    
    # Cancel any remaining tasks
    for task in asyncio.all_tasks():
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
                
    # Clear scheduled timers
    for handle in hass.loop._scheduled:
        handle.cancel()

@pytest.mark.asyncio
async def test_coordinator_data_processing(coordinator: RTL433Coordinator) -> None:
    """Test the coordinator's data processing capabilities.
    
    Verifies that the coordinator correctly processes different types of data:
    1. Valid sensor data with all required fields
    2. Valid data from different models
    3. Invalid data (non-dict)
    4. Incomplete data (missing required fields)
    
    Args:
        coordinator: Test coordinator instance
    """
    test_cases: List[Tuple[Any, int]] = [
        ({"model": "Acurite-Tower", "id": 1234, "temperature_C": 22.5}, 1),
        ({"model": "Other-Model", "id": 5678}, 1),
        ("not a dict", 1),
        ({"temperature_C": 22.5}, 1)  # Missing model and id
    ]

    for test_data, expected_length in test_cases:
        coordinator._process_data(test_data)
        assert len(coordinator.data) == expected_length

@pytest.mark.asyncio
async def test_coordinator_process_management(
    coordinator: RTL433Coordinator, 
    mock_process_cleanup: AsyncMock
) -> None:
    """Test RTL-433 process management functionality.
    
    Verifies that the coordinator properly:
    1. Starts the RTL-433 process
    2. Initializes monitoring tasks
    3. Handles process shutdown
    4. Cleans up resources
    
    Args:
        coordinator: Test coordinator instance
        mock_process_cleanup: Mock for process cleanup operations
    """
    mock_process = mock_process_cleanup.return_value
    mock_process._is_mock = True
    mock_process.returncode = None
    mock_process.stdout.readline = AsyncMock(return_value=b'{"model":"Test","id":1234}\n')
    mock_process.stderr.read = AsyncMock(return_value=b"")
    mock_process.wait = AsyncMock(return_value=0)
    mock_process.terminate = AsyncMock()

    await coordinator._start_rtl433()
    assert coordinator._process is not None
    assert coordinator._read_task is not None
    assert coordinator._monitor_task is not None

    await coordinator.shutdown()
    assert coordinator._shutdown is True
    assert coordinator._process is None

@pytest.mark.asyncio
async def test_coordinator_process_timeout(
    coordinator: RTL433Coordinator, 
    hass: HomeAssistant
) -> None:
    """Test handling of RTL-433 process timeouts.
    
    Verifies that the coordinator properly handles:
    1. Process output timeouts
    2. Resource cleanup after timeout
    3. Task cancellation
    
    Args:
        coordinator: Test coordinator instance
        hass: HomeAssistant instance for test environment
    """
    mock_process = AsyncMock()
    mock_process._is_mock = True
    mock_process.returncode = None
    mock_process.stdout = AsyncMock()
    mock_process.stderr = AsyncMock()
    mock_process.stdout.readline = AsyncMock(side_effect=asyncio.TimeoutError)
    mock_process.stderr.read = AsyncMock(return_value=b"")
    mock_process.wait = AsyncMock(return_value=0)
    mock_process.terminate = AsyncMock()

    with patch('asyncio.create_subprocess_exec', return_value=mock_process):
        await coordinator._start_rtl433()
        assert coordinator._process is not None
        assert coordinator._read_task is not None

        # Wait for timeout handling
        await wait_for_cleanup()
        assert coordinator._process is None

@pytest.mark.asyncio
async def test_coordinator_stderr_timeout(
    coordinator: RTL433Coordinator, 
    hass: HomeAssistant
) -> None:
    """Test handling of stderr read timeouts.
    
    Verifies that the coordinator properly handles:
    1. Stderr read timeouts
    2. Continued process operation
    3. Resource cleanup
    
    Args:
        coordinator: Test coordinator instance
        hass: HomeAssistant instance for test environment
    """
    mock_process = AsyncMock()
    mock_process._is_mock = True
    mock_process.returncode = None
    mock_process.stdout = AsyncMock()
    mock_process.stderr = AsyncMock()
    mock_process.stdout.readline = AsyncMock(return_value=b'{"model":"Test","id":1234}\n')
    mock_process.stderr.read = AsyncMock(side_effect=asyncio.TimeoutError)
    mock_process.wait = AsyncMock(return_value=0)
    mock_process.terminate = AsyncMock()

    with patch('asyncio.create_subprocess_exec', return_value=mock_process):
        await coordinator._start_rtl433()
        assert coordinator._process is not None
        assert coordinator._monitor_task is not None

        # Wait for timeout handling
        await wait_for_cleanup()
        assert coordinator._process is None

@pytest.mark.asyncio
async def test_coordinator_cleanup_on_start(
    coordinator: RTL433Coordinator, 
    hass: HomeAssistant
) -> None:
    """Test coordinator cleanup operations during startup.
    
    Verifies that the coordinator:
    1. Cleans up existing resources before start
    2. Initializes new process and tasks
    3. Performs proper shutdown
    
    Args:
        coordinator: Test coordinator instance
        hass: HomeAssistant instance for test environment
    """
    mock_process = AsyncMock()
    mock_process._is_mock = True
    mock_process.returncode = None
    mock_process.stdout = AsyncMock()
    mock_process.stderr = AsyncMock()
    mock_process.stdout.readline = AsyncMock(return_value=b'{"model":"Test","id":1234}\n')
    mock_process.stderr.read = AsyncMock(return_value=b"")
    mock_process.wait = AsyncMock(return_value=0)
    mock_process.terminate = AsyncMock()

    with patch('asyncio.create_subprocess_exec', return_value=mock_process):
        await coordinator._start_rtl433()
        assert coordinator._process is not None
        assert coordinator._read_task is not None
        assert coordinator._monitor_task is not None

        await coordinator.shutdown()
        await wait_for_cleanup()
        assert coordinator._shutdown is True
        assert coordinator._process is None

@pytest.mark.asyncio
async def test_coordinator_cleanup_on_error(
    coordinator: RTL433Coordinator, 
    hass: HomeAssistant
) -> None:
    """Test cleanup operations when errors occur.
    
    Verifies that the coordinator properly:
    1. Handles process errors
    2. Cleans up resources after errors
    3. Maintains consistent state
    
    Args:
        coordinator: Test coordinator instance
        hass: HomeAssistant instance for test environment
    """
    mock_process = AsyncMock()
    mock_process._is_mock = True
    mock_process.returncode = None
    mock_process.stdout = AsyncMock()
    mock_process.stderr = AsyncMock()
    mock_process.stdout.readline = AsyncMock(side_effect=Exception("Test error"))
    mock_process.stderr.read = AsyncMock(return_value=b"")
    mock_process.wait = AsyncMock(return_value=0)
    mock_process.terminate = AsyncMock()

    with patch('asyncio.create_subprocess_exec', return_value=mock_process):
        try:
            await coordinator._start_rtl433()
        except ConfigEntryNotReady:
            pass

        # Wait for cleanup completion
        await wait_for_cleanup()
        assert coordinator._process is None
        assert coordinator._read_task is None
        assert coordinator._monitor_task is None

@pytest.mark.asyncio
async def test_coordinator_shutdown(
    coordinator: RTL433Coordinator, 
    hass: HomeAssistant
) -> None:
    """Test coordinator shutdown process.
    
    Verifies that the coordinator:
    1. Properly shuts down the RTL-433 process
    2. Cancels all monitoring tasks
    3. Cleans up resources
    4. Maintains consistent state
    
    Args:
        coordinator: Test coordinator instance
        hass: HomeAssistant instance for test environment
    """
    mock_process = AsyncMock()
    mock_process._is_mock = True
    mock_process.returncode = None
    mock_process.stdout = AsyncMock()
    mock_process.stderr = AsyncMock()
    mock_process.stdout.readline = AsyncMock(return_value=b'{"model":"Test","id":1234}\n')
    mock_process.stderr.read = AsyncMock(return_value=b"")
    mock_process.wait = AsyncMock(return_value=0)
    mock_process.terminate = AsyncMock()

    with patch('asyncio.create_subprocess_exec', return_value=mock_process):
        await coordinator._start_rtl433()
        assert coordinator._process is not None
        
        await coordinator.shutdown()
        await wait_for_cleanup()
        
        assert coordinator._shutdown is True
        assert coordinator._process is None
        assert coordinator._read_task is None
        assert coordinator._monitor_task is None

@pytest.mark.asyncio
async def test_error_rate_limiting(coordinator: RTL433Coordinator) -> None:
    """Test error rate limiting functionality.
    
    Verifies that:
    1. Errors are logged initially
    2. Frequent errors are rate limited
    3. Rate limiting resets after timeout
    4. Different error types are tracked separately
    
    Args:
        coordinator: Test coordinator instance
    """
    # Test initial error logging
    assert coordinator._should_log_error("test_error") is True
    assert coordinator._should_log_error("test_error") is True
    assert coordinator._should_log_error("test_error") is True
    
    # Test rate limiting after threshold
    assert coordinator._should_log_error("test_error") is False
    assert coordinator._should_log_error("test_error") is False
    
    # Test different error types are tracked separately
    assert coordinator._should_log_error("different_error") is True
    
    # Test rate limit reset after timeout
    coordinator._error_counts["test_error"] = (1, time.time() - 301)  # Past timeout
    assert coordinator._should_log_error("test_error") is True

@pytest.mark.asyncio
async def test_exponential_backoff(
    coordinator: RTL433Coordinator,
    hass: HomeAssistant
) -> None:
    """Test exponential backoff for retry attempts.
    
    Verifies that:
    1. Retry delays increase exponentially
    2. Maximum retry delay is capped
    3. Retry count is tracked correctly
    
    Args:
        coordinator: Test coordinator instance
        hass: HomeAssistant instance for test environment
    """
    mock_process = AsyncMock()
    mock_process._is_mock = True
    mock_process.returncode = 1  # Simulate failure
    
    sleep_times = []
    
    async def mock_sleep(delay):
        sleep_times.append(delay)
    
    with patch('asyncio.create_subprocess_exec', side_effect=Exception("Test error")), \
         patch('asyncio.sleep', new=mock_sleep):
        
        # Test multiple retry attempts
        for _ in range(3):
            try:
                await coordinator._async_update_data()
            except UpdateFailed:
                pass
    
    # Verify exponential backoff
    assert len(sleep_times) == 3
    assert sleep_times[0] == 5  # First retry: 5 seconds
    assert sleep_times[1] == 10  # Second retry: 10 seconds
    assert sleep_times[2] == 20  # Third retry: 20 seconds

@pytest.mark.asyncio
async def test_error_context_preservation(
    coordinator: RTL433Coordinator,
    hass: HomeAssistant,
    caplog: LogCaptureFixture,
) -> None:
    """Test preservation of error context during failures.
    
    Verifies that:
    1. Error messages include relevant context
    2. Error types are properly categorized
    3. Error handling chain is maintained
    
    Args:
        coordinator: Test coordinator instance
        hass: HomeAssistant instance for test environment
        caplog: Pytest fixture for capturing log messages
    """
    mock_process = AsyncMock()
    mock_process._is_mock = True
    mock_process.returncode = None
    mock_process.stdout = AsyncMock()
    mock_process.stderr = AsyncMock()
    
    # Test JSON decode error
    mock_process.stdout.readline = AsyncMock(return_value=b'invalid json')
    
    with patch('asyncio.create_subprocess_exec', return_value=mock_process):
        await coordinator._start_rtl433()
        # Allow error to be processed
        await asyncio.sleep(0.1)
        
        # Verify error was logged with context
        assert any(
            "Failed to parse RTL-433 JSON data" in record.message
            for record in caplog.records
            if record.levelname == "WARNING"
        )
    
    # Clear captured logs
    caplog.clear()
    
    # Test process error with stderr message
    error_message = "USB error occurred"
    mock_process.stderr.read = AsyncMock(return_value=error_message.encode())
    
    with patch('asyncio.create_subprocess_exec', return_value=mock_process):
        try:
            await coordinator._start_rtl433()
            await asyncio.sleep(0.1)  # Allow error to be processed
        except ConfigEntryNotReady as err:
            assert error_message in str(err)
            assert any(
                error_message in record.message
                for record in caplog.records
                if record.levelname == "ERROR"
            )

@pytest.mark.asyncio
async def test_device_reconnection_backoff(
    coordinator: RTL433Coordinator,
    hass: HomeAssistant,
    caplog: LogCaptureFixture,
) -> None:
    """Test device reconnection backoff strategy.
    
    Verifies that:
    1. Initial connection attempts use minimal delay
    2. Subsequent failures increase backoff time
    3. Successful connection resets backoff
    4. Maximum backoff time is enforced
    
    Args:
        coordinator: Test coordinator instance
        hass: HomeAssistant instance
        caplog: Fixture for capturing log messages
    """
    # Mock time functions to control timing
    current_time = 0.0
    
    def mock_time():
        return current_time
    
    sleep_times = []
    
    async def mock_sleep(delay):
        sleep_times.append(delay)
        nonlocal current_time
        current_time += delay
    
    with patch('time.time', new=mock_time), \
         patch('asyncio.sleep', new=mock_sleep):
        
        # Test initial connection attempt
        mock_process = AsyncMock()
        mock_process._is_mock = True
        mock_process.returncode = 1
        
        with patch('asyncio.create_subprocess_exec', 
                  side_effect=Exception("Connection failed")):
            try:
                await coordinator._handle_device_connection()
            except ConfigEntryNotReady:
                pass
        
        # Verify initial backoff
        assert len(sleep_times) == 1
        assert sleep_times[0] == coordinator._current_backoff_time
        
        # Test increasing backoff
        sleep_times.clear()
        for _ in range(3):
            try:
                await coordinator._handle_device_connection()
            except ConfigEntryNotReady:
                pass
        
        # Verify backoff increases
        assert len(sleep_times) == 3
        assert sleep_times[1] > sleep_times[0]
        assert sleep_times[2] > sleep_times[1]
        
        # Test maximum backoff limit
        sleep_times.clear()
        coordinator._connection_attempts = 10  # Force high backoff
        
        try:
            await coordinator._handle_device_connection()
        except ConfigEntryNotReady:
            pass
        
        assert sleep_times[0] <= coordinator.MAX_BACKOFF_TIME

@pytest.mark.asyncio
async def test_backoff_reset_after_success(
    coordinator: RTL433Coordinator,
    hass: HomeAssistant,
) -> None:
    """Test backoff reset after successful connection.
    
    Verifies that:
    1. Backoff state is reset after successful connection
    2. Connection metrics are updated properly
    3. Subsequent failures start with initial backoff
    
    Args:
        coordinator: Test coordinator instance
        hass: HomeAssistant instance
    """
    current_time = 0.0
    
    def mock_time():
        return current_time
    
    with patch('time.time', new=mock_time):
        # Simulate some failed attempts
        coordinator._connection_attempts = 5
        coordinator._current_backoff_time = 100
        
        # Simulate successful connection
        mock_process = AsyncMock()
        mock_process._is_mock = True
        mock_process.returncode = None
        mock_process.stdout = AsyncMock()
        mock_process.stderr = AsyncMock()
        mock_process.stdout.readline = AsyncMock(return_value=b'{"model":"Test","id":1234}\n')
        mock_process.stderr.read = AsyncMock(return_value=b"")
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            await coordinator._handle_device_connection()
        
        # Verify connection state reset
        assert coordinator._connection_attempts == 0
        assert coordinator._current_backoff_time == coordinator.INITIAL_BACKOFF_TIME
        assert coordinator._last_successful_connection == current_time

@pytest.mark.asyncio
async def test_connection_error_handling(
    coordinator: RTL433Coordinator,
    hass: HomeAssistant,
    caplog: LogCaptureFixture,
) -> None:
    """Test connection error handling and logging.
    
    Verifies that:
    1. Different error types are handled appropriately
    2. Error messages are properly logged
    3. Connection state is updated on errors
    4. Cleanup is performed after errors
    
    Args:
        coordinator: Test coordinator instance
        hass: HomeAssistant instance
        caplog: Fixture for capturing log messages
    """
    # Test USB error handling
    mock_process = AsyncMock()
    mock_process._is_mock = True
    mock_process.returncode = None
    mock_process.stdout = AsyncMock()
    mock_process.stderr = AsyncMock()
    mock_process.stderr.read = AsyncMock(return_value=b"usb_claim_interface error")
    
    with patch('asyncio.create_subprocess_exec', return_value=mock_process):
        try:
            await coordinator._handle_device_connection()
        except ConfigEntryNotReady as err:
            assert "device is in use" in str(err).lower()
    
    # Verify error logging
    assert any(
        "Failed to connect to RTL-433 device" in record.message
        for record in caplog.records
        if record.levelname == "ERROR"
    )
    
    # Test device not found error
    caplog.clear()
    mock_process.stderr.read = AsyncMock(return_value=b"not found")
    
    with patch('asyncio.create_subprocess_exec', return_value=mock_process):
        try:
            await coordinator._handle_device_connection()
        except ConfigEntryNotReady as err:
            assert "not found" in str(err).lower()
    
    # Verify connection state
    assert coordinator._last_successful_connection == 0
    assert coordinator._process is None

@pytest.mark.asyncio
async def test_protocol_validation(
    coordinator: RTL433Coordinator,
    caplog: LogCaptureFixture,
) -> None:
    """Test protocol validation functionality.
    
    Verifies that:
    1. Valid protocols are accepted
    2. Invalid protocols are rejected
    3. Protocol filtering works correctly
    4. Error messages are properly logged
    
    Args:
        coordinator: Test coordinator instance
        caplog: Fixture for capturing log messages
    """
    # Test valid protocol
    valid_data = {
        "model": "Acurite-5n1",
        "id": 1234,
        "temperature_F": 72.5,
        "humidity": 45,
    }
    coordinator._process_data(valid_data)
    assert f"Acurite-5n1_1234" in coordinator.data
    
    # Test invalid protocol
    invalid_data = {
        "model": "Invalid-Model",
        "id": 5678,
        "temperature_C": 22.5,
    }
    coordinator._process_data(invalid_data)
    assert "Invalid-Model_5678" not in coordinator.data
    assert any(
        "Unsupported protocol: Invalid-Model" in record.message
        for record in caplog.records
        if record.levelname == "WARNING"
    )
    
    # Test protocol filter
    coordinator._protocol_filter = {"Acurite-Tower"}
    filtered_data = {
        "model": "Acurite-5n1",  # Valid but filtered
        "id": 9012,
        "temperature_F": 75.0,
    }
    coordinator._process_data(filtered_data)
    assert "Acurite-5n1_9012" not in coordinator.data

@pytest.mark.asyncio
async def test_value_validation(
    coordinator: RTL433Coordinator,
    caplog: LogCaptureFixture,
) -> None:
    """Test sensor value validation.
    
    Verifies that:
    1. Values within range are accepted
    2. Values outside range are rejected
    3. Step size validation works
    4. Error messages are properly logged
    
    Args:
        coordinator: Test coordinator instance
        caplog: Fixture for capturing log messages
    """
    # Test valid values
    valid_data = {
        "model": "Acurite-5n1",
        "id": 1234,
        "temperature_F": 72.5,
        "humidity": 45,
        "wind_avg_km_h": 15.5,
        "wind_dir_deg": 180,
        "rain_in": 0.25,
    }
    coordinator._process_data(valid_data)
    assert coordinator.data["Acurite-5n1_1234"]["temperature_F"] == 72.5
    
    # Test out of range values
    invalid_data = {
        "model": "Acurite-5n1",
        "id": 5678,
        "temperature_F": 200.0,  # Too high
        "humidity": 150,         # Too high
        "wind_dir_deg": 400,     # Too high
    }
    coordinator._process_data(invalid_data)
    device_id = "Acurite-5n1_5678"
    if device_id in coordinator.data:
        assert "temperature_F" not in coordinator.data[device_id]
        assert "humidity" not in coordinator.data[device_id]
        assert "wind_dir_deg" not in coordinator.data[device_id]
    
    # Verify error logging
    assert any(
        "Invalid temperature_F value" in record.message
        for record in caplog.records
        if record.levelname == "WARNING"
    )
    
    # Test step size validation
    step_data = {
        "model": "Acurite-5n1",
        "id": 9012,
        "temperature_F": 72.123,  # Invalid step (should be 0.1)
        "humidity": 45.5,         # Invalid step (should be 1)
    }
    coordinator._process_data(step_data)
    device_id = "Acurite-5n1_9012"
    if device_id in coordinator.data:
        assert "temperature_F" not in coordinator.data[device_id]
        assert "humidity" not in coordinator.data[device_id]

@pytest.mark.asyncio
async def test_protocol_configuration_validation(
    hass: HomeAssistant,
    caplog: LogCaptureFixture,
) -> None:
    """Test protocol configuration validation.
    
    Verifies that:
    1. Valid protocol configurations are accepted
    2. Invalid protocols in config are rejected
    3. Error messages are properly formatted
    
    Args:
        hass: HomeAssistant instance
        caplog: Fixture for capturing log messages
    """
    # Test valid configuration
    valid_config = {
        "device": "0",
        "protocol_filter": ["Acurite-5n1", "LaCrosse-TX141W"],
    }
    coordinator = RTL433Coordinator(hass, "test_entry", valid_config)
    assert len(coordinator._protocol_filter) == 2
    
    # Test invalid configuration
    invalid_config = {
        "device": "0",
        "protocol_filter": ["Invalid-Model", "Another-Invalid"],
    }
    with pytest.raises(ValueError) as excinfo:
        RTL433Coordinator(hass, "test_entry", invalid_config)
    
    assert "Invalid protocol specified" in str(excinfo.value)
    assert "Invalid-Model" in str(excinfo.value)
    assert "Another-Invalid" in str(excinfo.value)

@pytest.mark.asyncio
async def test_mixed_value_validation(
    coordinator: RTL433Coordinator,
    caplog: LogCaptureFixture,
) -> None:
    """Test validation of mixed valid and invalid values.
    
    Verifies that:
    1. Valid values are preserved when some are invalid
    2. Non-numeric values are handled correctly
    3. Special fields are preserved
    4. Partial updates work correctly
    
    Args:
        coordinator: Test coordinator instance
        caplog: Fixture for capturing log messages
    """
    mixed_data = {
        "model": "Acurite-5n1",
        "id": 1234,
        "temperature_F": 72.5,    # Valid
        "humidity": 150,          # Invalid
        "battery_ok": True,       # Non-numeric
        "message_type": 5,        # Special field
        "wind_dir_deg": "North",  # Invalid type
    }
    
    coordinator._process_data(mixed_data)
    device_data = coordinator.data.get("Acurite-5n1_1234", {})
    
    # Check valid values are preserved
    assert device_data.get("temperature_F") == 72.5
    assert device_data.get("battery_ok") is True
    assert device_data.get("message_type") == 5
    
    # Check invalid values are excluded
    assert "humidity" not in device_data
    assert "wind_dir_deg" not in device_data
    
    # Verify error logging
    assert any(
        "Invalid humidity value" in record.message
        for record in caplog.records
        if record.levelname == "WARNING"
    )
    assert any(
        "Failed to convert wind_dir_deg value" in record.message
        for record in caplog.records
        if record.levelname == "WARNING"
    )