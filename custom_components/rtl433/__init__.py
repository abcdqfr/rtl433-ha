"""The RTL-433 integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform, EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import (
    DOMAIN,
    CONF_DEVICE_ID,
    CONF_FREQUENCY,
    CONF_GAIN,
    CONF_PROTOCOL_FILTER,
)
from .coordinator import RTL433Coordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the RTL-433 component."""
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up RTL-433 from a config entry."""
    try:
        device_id = entry.data.get(CONF_DEVICE_ID, entry.data.get('device'))
        if device_id is None:
            raise KeyError('device_id or device not found')
    except KeyError as e:
        _LOGGER.error("Key error: %s. Entry data: %s", str(e), entry.data)
        return False

    coordinator = RTL433Coordinator(
        hass,
        device_id=device_id,
        frequency=entry.data[CONF_FREQUENCY],
        gain=entry.data[CONF_GAIN],
        protocol_filter=entry.data.get(CONF_PROTOCOL_FILTER),
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
    }

    # Register shutdown handler
    async def _shutdown_rtl433(event):
        """Shutdown RTL-433 process."""
        await coordinator.async_shutdown()

    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _shutdown_rtl433)
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
        await coordinator.async_shutdown()
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok