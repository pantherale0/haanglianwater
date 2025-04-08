"""Home Assistant Anglian Water Diagnostics"""

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, CONF_ACCESS_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from typing import Any
from homeassistant.helpers.device_registry import DeviceEntry

from pyanglianwater.enum import UsagesReadGranularity

from .const import DOMAIN, VERSION

REDACTED_FIELDS = [
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_ACCESS_TOKEN,
    "refresh_token",
]


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> dict[str, Any]:
    """Get diagnostics for a config entry."""
    entry = hass.data[DOMAIN][config_entry.entry_id]
    return {
        "config_entry": async_redact_data(config_entry.data, REDACTED_FIELDS),
        "options": async_redact_data(config_entry.options, REDACTED_FIELDS),
        "anglian_water": async_redact_data(entry.client.to_dict(), REDACTED_FIELDS),
        "metering_data": async_redact_data(
            await entry.client.get_usages(
                interval=UsagesReadGranularity.HOURLY,
                update_cache=False
            ),
            REDACTED_FIELDS
        )
    }


async def async_get_device_diagnostics(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    device_entry: DeviceEntry,
) -> dict[str, Any]:
    """Get diagnostics for a device entry."""
    entry = hass.data[DOMAIN][config_entry.entry_id]
    meter = entry.client.meters.get(device_entry.serial_number, None)
    if meter is not None:
        meter = meter.to_dict()
    else:
        meter = {}
    return {
        "device_entry": async_redact_data(device_entry.serial_number, REDACTED_FIELDS),
        "config_entry": async_redact_data(device_entry.config_entries, REDACTED_FIELDS),
        "device_id": device_entry.id,
        "serial": device_entry.serial_number,
        "meter": async_redact_data(meter, REDACTED_FIELDS),
    }
