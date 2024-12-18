"""Test configuration for RTL-433 integration tests."""
import asyncio
import logging
import pytest
import os
import socket
import tempfile
from unittest.mock import patch

from homeassistant import config_entries, loader
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.const import CONF_DEVICE_ID
from homeassistant.loader import DATA_COMPONENTS, DATA_MISSING_PLATFORMS
from homeassistant.setup import async_setup_component
from homeassistant.helpers import translation

from .test_cleanup import cleanup_utility, cleanup_test_environment
from .test_mocks import RTL433ProcessMock, HomeAssistantMock
from .test_fixtures import (
    mock_rtl433_data,
    mock_coordinator,
    mock_add_entities,
    mock_rtl433_process,
    enable_debug_logging,
    mock_config_entry
)

_LOGGER = logging.getLogger(__name__)

# Store original socket class
_OriginalSocket = socket.socket

class SocketProxy:
    """Proxy for socket operations that only allows Unix domain sockets."""
    def __new__(cls, family=-1, type=-1, proto=-1, fileno=None):
        if family == socket.AF_UNIX:
            return _OriginalSocket(family, type, proto, fileno)
        raise socket.error("Only Unix domain sockets are allowed")

@pytest.fixture
def event_loop():
    """Create an event loop for each test case."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()

@pytest.fixture(autouse=True)
def socket_control():
    """Control socket usage to only allow Unix domain sockets."""
    socket.socket = SocketProxy
    yield
    socket.socket = _OriginalSocket

@pytest.fixture(autouse=True)
async def auto_enable_custom_integrations(hass):
    """Enable custom integrations in Home Assistant."""
    hass.data.setdefault("custom_components", {})

@pytest.fixture
async def hass(tmp_path, event_loop, enable_debug_logging):
    """Fixture to provide a test instance of Home Assistant."""
    hass = HomeAssistant(str(tmp_path))
    
    # Set up minimum required configuration
    hass.config.config_dir = str(tmp_path)
    
    # Initialize required hass data
    hass.data["integrations"] = {}
    hass.data["entity_platform"] = {}
    hass.data["device_registry"] = {}
    hass.data["entity_registry"] = {}
    hass.data[DATA_COMPONENTS] = {}
    hass.data[DATA_MISSING_PLATFORMS] = {}
    
    # Initialize translation cache
    translation_cache = translation._TranslationCache(hass)
    hass.data["translation_cache"] = translation_cache
    hass.data["translation_flatten_cache"] = translation_cache
    
    # Initialize config entries
    hass.config_entries = config_entries.ConfigEntries(hass, {})
    await hass.config_entries.async_initialize()
    
    # Set up core config
    await async_setup_component(hass, "homeassistant", {})
    await async_setup_component(hass, "persistent_notification", {})
    
    await hass.async_start()
    
    _LOGGER.debug("Home Assistant test instance initialized")
    
    try:
        yield hass
    finally:
        # Cleanup
        _LOGGER.debug("Cleaning up Home Assistant test instance")
        await cleanup_test_environment()
        await hass.async_stop(force=True)
        _LOGGER.debug("Home Assistant test instance cleanup complete")

@pytest.fixture(autouse=True)
async def cleanup_after_test():
    """Cleanup after each test with debug reporting."""
    yield
    await cleanup_test_environment()
    _LOGGER.debug(cleanup_utility.get_cleanup_report())

@pytest.fixture(autouse=True)
def mock_process_cleanup():
    """Mock process cleanup with debug capabilities."""
    process_mock = RTL433ProcessMock()
    process_mock.configure_normal_operation()
    
    with patch('asyncio.create_subprocess_exec', return_value=process_mock):
        yield process_mock
        _LOGGER.debug(process_mock.get_debug_report())