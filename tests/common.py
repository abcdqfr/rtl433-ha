"""Common test utilities."""
from unittest.mock import patch
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.rtl433.const import (
    DOMAIN,
    CONF_DEVICE_ID,
    CONF_FREQUENCY,
    CONF_GAIN,
)

async def setup_rtl433_integration(hass, config=None):
    """Create the integration in Home Assistant."""
    config = config or {
        CONF_DEVICE_ID: "0",
        CONF_FREQUENCY: "433.92M",
        CONF_GAIN: 40,
    }

    with patch("custom_components.rtl433.coordinator.RTL433Coordinator._start_rtl433", return_value=None):
        entry = MockConfigEntry(
            domain=DOMAIN,
            data=config,
            entry_id="test",
            unique_id=f"rtl433_{config[CONF_DEVICE_ID]}"
        )
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        return entry