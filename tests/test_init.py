"""Test the RTL-433 integration."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from custom_components.rtl433 import (
    async_setup,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.rtl433.const import DOMAIN

@pytest.fixture
def mock_setup_entry():
    """Mock setup entry."""
    with patch('homeassistant.config_entries.ConfigEntries.async_forward_entry_setup',
              return_value=True) as forward_mock:
        yield forward_mock

@pytest.fixture
def mock_unload_entry():
    """Mock unload entry."""
    with patch('homeassistant.config_entries.ConfigEntries.async_unload_platforms',
              return_value=True) as unload_mock:
        yield unload_mock

@pytest.mark.asyncio
async def test_setup_with_config(hass: HomeAssistant):
    """Test setup with config."""
    config = {DOMAIN: {}}
    assert await async_setup(hass, config)
    assert DOMAIN in hass.data

@pytest.mark.asyncio
async def test_setup_entry(hass: HomeAssistant, mock_setup_entry):
    """Test setup entry."""
    entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="RTL-433 Test",
        data={
            "device": "0",
            "frequency": "433.92M",
            "gain": 40,
        },
        source="test",
        options={},
        unique_id="test_unique_id",
        entry_id="test_entry",
    )

    with patch('custom_components.rtl433.coordinator.RTL433Coordinator') as mock_coordinator:
        mock_coordinator_instance = mock_coordinator.return_value
        mock_coordinator_instance.async_config_entry_first_refresh = AsyncMock()
        
        assert await async_setup_entry(hass, entry)
        assert DOMAIN in hass.data
        assert entry.entry_id in hass.data[DOMAIN]
        assert isinstance(hass.data[DOMAIN][entry.entry_id], dict)
        assert "coordinator" in hass.data[DOMAIN][entry.entry_id]
        
        # Verify platform setup
        mock_setup_entry.assert_called_once_with(entry, Platform.SENSOR)

@pytest.mark.asyncio
async def test_unload_entry(hass: HomeAssistant, mock_unload_entry):
    """Test unloading an entry."""
    entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="RTL-433 Test",
        data={
            "device": "0",
            "frequency": "433.92M",
            "gain": 40,
        },
        source="test",
        options={},
        unique_id="test_unique_id",
        entry_id="test_entry",
    )

    with patch('custom_components.rtl433.coordinator.RTL433Coordinator') as mock_coordinator:
        mock_coordinator_instance = mock_coordinator.return_value
        mock_coordinator_instance.async_config_entry_first_refresh = AsyncMock()
        mock_coordinator_instance.shutdown = AsyncMock()
        
        await async_setup_entry(hass, entry)
        assert await async_unload_entry(hass, entry)
        assert entry.entry_id not in hass.data[DOMAIN]
        
        # Verify platform unload
        mock_unload_entry.assert_called_once_with(entry, [Platform.SENSOR])

@pytest.mark.asyncio
async def test_setup_multiple_entries(hass: HomeAssistant, mock_setup_entry):
    """Test setting up multiple entries."""
    entries = [
        ConfigEntry(
            version=1,
            minor_version=1,
            domain=DOMAIN,
            title=f"RTL-433 Test {i}",
            data={
                "device": str(i),
                "frequency": "433.92M",
                "gain": 40,
            },
            source="test",
            options={},
            unique_id=f"test_unique_id_{i}",
            entry_id=f"test_entry_{i}",
        )
        for i in range(2)
    ]

    with patch('custom_components.rtl433.coordinator.RTL433Coordinator') as mock_coordinator:
        mock_coordinator_instance = mock_coordinator.return_value
        mock_coordinator_instance.async_config_entry_first_refresh = AsyncMock()
        
        for entry in entries:
            assert await async_setup_entry(hass, entry)
            assert entry.entry_id in hass.data[DOMAIN]
            assert isinstance(hass.data[DOMAIN][entry.entry_id], dict)
            assert "coordinator" in hass.data[DOMAIN][entry.entry_id]
            
            # Verify platform setup for each entry
            mock_setup_entry.assert_any_call(entry, Platform.SENSOR)