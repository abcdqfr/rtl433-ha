"""Test the RTL-433 config flow."""
import asyncio
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from homeassistant import config_entries, data_entry_flow
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.const import CONF_DEVICE_ID

from custom_components.rtl433.config_flow import RTL433FlowHandler, validate_rtl433_device
from custom_components.rtl433.const import (
    DOMAIN,
    CONF_FREQUENCY,
    CONF_GAIN,
    CONF_PROTOCOL_FILTER,
    DEFAULT_FREQUENCY,
    DEFAULT_GAIN,
)

@pytest.fixture
async def mock_hass():
    """Mock Home Assistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    yield hass

@pytest.fixture
async def flow(mock_hass):
    """Get a configured flow."""
    flow = RTL433FlowHandler()
    flow.hass = mock_hass
    flow.context = {}
    flow.async_get_current_entries = AsyncMock(return_value=[])
    flow.async_set_unique_id = AsyncMock()
    return flow

@pytest.mark.asyncio
async def test_validate_rtl433_device_success():
    """Test successful device validation."""
    with patch('asyncio.create_subprocess_exec', new_callable=AsyncMock) as mock_exec:
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (None, b"")
        mock_process.returncode = 0
        mock_exec.return_value = mock_process
        
        is_valid, error = await validate_rtl433_device("0")
        assert is_valid is True
        assert error is None
        
        # Verify correct command construction
        mock_exec.assert_called_once()
        cmd_args = mock_exec.call_args[0]
        assert "-d" in cmd_args and "0" in cmd_args
        assert "-F" in cmd_args and "null" in cmd_args

@pytest.mark.asyncio
async def test_validate_rtl433_device_in_use():
    """Test device in use error."""
    with patch('asyncio.create_subprocess_exec', new_callable=AsyncMock) as mock_exec:
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (None, b"usb_claim_interface error")
        mock_process.returncode = 1
        mock_exec.return_value = mock_process
        
        is_valid, error = await validate_rtl433_device("0")
        assert is_valid is False
        assert error == "Device is in use"

@pytest.mark.asyncio
async def test_validate_rtl433_device_not_found():
    """Test device not found error."""
    with patch('asyncio.create_subprocess_exec', new_callable=AsyncMock) as mock_exec:
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (None, b"not found")
        mock_process.returncode = 1
        mock_exec.return_value = mock_process
        
        is_valid, error = await validate_rtl433_device("0")
        assert is_valid is False
        assert error == "RTL-SDR device not found"

@pytest.mark.asyncio
async def test_validate_rtl433_not_installed():
    """Test rtl_433 not installed error."""
    with patch('asyncio.create_subprocess_exec', side_effect=FileNotFoundError):
        is_valid, error = await validate_rtl433_device("0")
        assert is_valid is False
        assert error == "rtl_433 not installed"

@pytest.mark.asyncio
async def test_flow_user_init(flow):
    """Test the initialization of the form in the first step of the config flow."""
    result = await flow.async_step_user(user_input=None)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}
    
    # Verify schema has all required fields
    schema = result["data_schema"].schema
    assert CONF_DEVICE_ID in schema
    assert CONF_FREQUENCY in schema
    assert CONF_GAIN in schema
    assert CONF_PROTOCOL_FILTER in schema

@pytest.mark.asyncio
async def test_flow_user_device_validation_success(flow):
    """Test successful device validation in config flow."""
    with patch('custom_components.rtl433.config_flow.validate_rtl433_device',
              return_value=(True, None)):
        result = await flow.async_step_user({
            CONF_DEVICE_ID: "0",
            CONF_FREQUENCY: DEFAULT_FREQUENCY,
            CONF_GAIN: DEFAULT_GAIN,
            CONF_PROTOCOL_FILTER: [],
        })
        
        assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result["title"] == "RTL-433 Sensor"
        assert result["data"] == {
            CONF_DEVICE_ID: "0",
            CONF_FREQUENCY: DEFAULT_FREQUENCY,
            CONF_GAIN: DEFAULT_GAIN,
            CONF_PROTOCOL_FILTER: [],
        }

@pytest.mark.asyncio
async def test_flow_user_validation_error(flow):
    """Test error handling in config flow."""
    with patch('custom_components.rtl433.config_flow.validate_rtl433_device',
              return_value=(False, "Test error")):
        result = await flow.async_step_user({
            CONF_DEVICE_ID: "0",
            CONF_FREQUENCY: DEFAULT_FREQUENCY,
            CONF_GAIN: DEFAULT_GAIN,
        })
        
        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "user"
        assert result["errors"]["base"] == "Test error"

@pytest.mark.asyncio
async def test_flow_user_invalid_frequency(flow):
    """Test frequency validation in config flow."""
    with patch('custom_components.rtl433.config_flow.validate_rtl433_device',
              return_value=(False, "Invalid frequency")):
        result = await flow.async_step_user({
            CONF_DEVICE_ID: "0",
            CONF_FREQUENCY: "invalid",
            CONF_GAIN: DEFAULT_GAIN,
        })
        
        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "user"
        assert result["errors"]["base"] == "Invalid frequency"

@pytest.mark.asyncio
async def test_flow_user_invalid_gain(flow):
    """Test gain validation in config flow."""
    with patch('custom_components.rtl433.config_flow.validate_rtl433_device',
              return_value=(False, "Invalid gain")):
        result = await flow.async_step_user({
            CONF_DEVICE_ID: "0",
            CONF_FREQUENCY: DEFAULT_FREQUENCY,
            CONF_GAIN: -1,  # Invalid gain value
        })
        
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"
        assert result["errors"]["base"] == "Invalid gain"