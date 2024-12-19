"""Config flow for RTL-433 integration."""
from __future__ import annotations

import asyncio
import re
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import (
    DOMAIN,
    CONF_DEVICE_ID,
    CONF_FREQUENCY,
    CONF_GAIN,
    CONF_PROTOCOL_FILTER,
    DEFAULT_FREQUENCY,
    DEFAULT_GAIN,
    DEFAULT_DEVICE_ID,
)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DEVICE_ID, default=DEFAULT_DEVICE_ID): str,
        vol.Required(CONF_FREQUENCY, default=DEFAULT_FREQUENCY): str,
        vol.Required(CONF_GAIN, default=DEFAULT_GAIN): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=50)
        ),
        vol.Optional(CONF_PROTOCOL_FILTER, default=""): str,
    }
)

class RTL433ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for RTL-433."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._device_id: Optional[str] = None

    async def async_step_user(
        self, 
        user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            try:
                # Extract and validate configuration
                device_id = str(user_input[CONF_DEVICE_ID])
                frequency = user_input[CONF_FREQUENCY]
                gain = user_input[CONF_GAIN]
                protocol_filter = user_input.get(CONF_PROTOCOL_FILTER, "")

                # Validate device ID format
                if not re.match(r"^\d+$", device_id):
                    errors[CONF_DEVICE_ID] = "invalid_device_id"

                # Validate frequency format
                if not re.match(r"^\d+(\.\d+)?M?$", frequency):
                    errors[CONF_FREQUENCY] = "invalid_frequency"

                # Validate gain range
                if not 0 <= gain <= 50:
                    errors[CONF_GAIN] = "invalid_gain"

                # Convert protocol filter from string to list
                protocol_list = []
                if protocol_filter:
                    protocol_list = [p.strip() for p in protocol_filter.split(",")]

                if not errors:
                    # Create unique ID and check if already configured
                    await self.async_set_unique_id(f"rtl433_{device_id}")
                    self._abort_if_unique_id_configured()

                    # Create config entry
                    return self.async_create_entry(
                        title=f"RTL-433 Device {device_id}",
                        data={
                            CONF_DEVICE_ID: device_id,
                            CONF_FREQUENCY: frequency,
                            CONF_GAIN: gain,
                            CONF_PROTOCOL_FILTER: protocol_list,
                        },
                    )

            except Exception as err:
                errors["base"] = "unknown"
                self.logger.exception("Unexpected error: %s", err)

        # Show form with any errors
        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        ) 