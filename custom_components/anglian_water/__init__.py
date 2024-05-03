"""Custom integration to integrate integration_blueprint with Home Assistant.

For more details about this integration, please refer to
https://github.com/ludeeus/integration_blueprint
"""

from __future__ import annotations
from datetime import date

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import ConfigEntryNotReady
from pyanglianwater import AnglianWater, API
from pyanglianwater.exceptions import ServiceUnavailableError


from .const import (
    DOMAIN,
    CONF_DEVICE_ID,
    CONF_TARIFF,
    CONF_CUSTOM_RATE,
    SVC_GET_USAGES_SCHEMA,
    SVC_FORCE_REFRESH_STATISTICS,
)
from .coordinator import AnglianWaterDataUpdateCoordinator

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
]


# https://developers.home-assistant.io/docs/config_entries_index/#setting-up-an-entry
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up this integration using UI."""
    try:
        _api = await API.create_via_login_existing_device(
            entry.data[CONF_USERNAME],
            entry.data[CONF_PASSWORD],
            entry.data[CONF_DEVICE_ID],
        )
        _aw = AnglianWater()
        _aw.api = _api
        _aw.current_tariff = entry.data.get(CONF_TARIFF, None)
        _aw.current_tariff_rate = entry.data.get(CONF_CUSTOM_RATE, None)
        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][entry.entry_id] = coordinator = (
            AnglianWaterDataUpdateCoordinator(hass=hass, client=_aw)
        )
        # https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
        await coordinator.async_config_entry_first_refresh()

        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        entry.async_on_unload(entry.add_update_listener(async_reload_entry))

        # load service to request data for a specific time frame
        async def get_readings(call: ServiceCall) -> ServiceResponse:
            """Handle a request to get readings."""
            return await _aw.get_usages(
                start=date.fromisoformat(call.data["start"]),
                end=date.fromisoformat(call.data["end"]),
            )

        hass.services.async_register(
            domain=DOMAIN,
            service="get_readings",
            service_func=get_readings,
            supports_response=SupportsResponse.ONLY,
            schema=SVC_GET_USAGES_SCHEMA,
        )

        # service call to force refresh data in database
        async def force_refresh_statistics(call: ServiceCall):
            """Handle a request to force refresh stats."""
            await coordinator.insert_statistics(
                start_date=date.fromisoformat(call.data["start"]),
                end_date=date.fromisoformat(call.data["end"]),
            )

        hass.services.async_register(
            domain=DOMAIN,
            service="force_refresh_statistics",
            service_func=force_refresh_statistics,
            supports_response=SupportsResponse.NONE,
            schema=SVC_FORCE_REFRESH_STATISTICS,
        )

        return True
    except ServiceUnavailableError as exception:
        raise ConfigEntryNotReady(
            exception, translation_domain=DOMAIN, translation_key="maintenance"
        ) from exception


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    if unloaded := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


# pylint: disable=unused-argument
async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate config entry."""
    return True
