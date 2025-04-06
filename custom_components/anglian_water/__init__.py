"""Custom integration to integration Anglian Water into Home Assistant.

This integration is not endoursed or supported by Anglian Water.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, CONF_ACCESS_TOKEN, Platform
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pyanglianwater import AnglianWater
from pyanglianwater.auth import MSOB2CAuth
from pyanglianwater.exceptions import ServiceUnavailableError


from .const import (
    DOMAIN,
    CONF_AREA,
    CONF_ACCOUNT_ID,
    CONF_TARIFF,
    CONF_CUSTOM_RATE
)
from .coordinator import AnglianWaterDataUpdateCoordinator

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
]


# https://developers.home-assistant.io/docs/config_entries_index/#setting-up-an-entry
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up this integration using UI."""
    try:
        _api = MSOB2CAuth(
            username=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
            account_id=entry.data[CONF_ACCOUNT_ID],
            refresh_token=entry.data.get(CONF_ACCESS_TOKEN, None),
            session=async_get_clientsession(hass),
        )
        await _api.send_login_request()
        _aw = await AnglianWater.create_from_authenticator(
            authenticator=_api,
            area=entry.data.get(CONF_AREA, None),
            tariff=entry.data.get(CONF_TARIFF, None),
            custom_rate=entry.data.get(CONF_CUSTOM_RATE, None)
        )
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
            return await _aw.get_usages()

        hass.services.async_register(
            domain=DOMAIN,
            service="get_readings",
            service_func=get_readings,
            supports_response=SupportsResponse.ONLY
        )

        # service call to force refresh data in database
        async def force_refresh_statistics(call: ServiceCall):
            """Handle a request to force refresh stats."""
            await coordinator.insert_statistics()

        hass.services.async_register(
            domain=DOMAIN,
            service="force_refresh_statistics",
            service_func=force_refresh_statistics,
            supports_response=SupportsResponse.NONE
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
