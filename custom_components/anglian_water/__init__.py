"""Custom integration to integration Anglian Water into Home Assistant.

This integration is not endoursed or supported by Anglian Water.
"""

from __future__ import annotations

import logging

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
from homeassistant.helpers import issue_registry as ir
from pyanglianwater import AnglianWater
from pyanglianwater.auth import MSOB2CAuth
from pyanglianwater.exceptions import ServiceUnavailableError


from .const import (
    DOMAIN,
    CONF_AREA,
    CONF_ACCOUNT_ID,
    CONF_TARIFF,
    CONF_CUSTOM_RATE,
    CONF_VERSION
)
from .coordinator import AnglianWaterDataUpdateCoordinator

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up this integration using UI."""
    if entry.version == CONF_VERSION:
        ir.async_delete_issue(hass, DOMAIN, "manual_migration")
    if entry.version < CONF_VERSION:
        return False
    try:
        _api = MSOB2CAuth(
            username=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
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
        await coordinator.async_config_entry_first_refresh()

        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        entry.async_on_unload(entry.add_update_listener(async_reload_entry))

        # load service to request data for a specific time frame
        async def get_readings(call: ServiceCall) -> ServiceResponse:
            """Handle a request to get readings."""
            await _aw.get_usages()
            return {
                k: v.to_dict() for k, v in _aw.meters.items()
            }

        hass.services.async_register(
            domain=DOMAIN,
            service="get_readings",
            service_func=get_readings,
            supports_response=SupportsResponse.ONLY
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


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate config entry."""
    _LOGGER.debug("Migrating configuration from version %s",
                  entry.version)
    new_data = entry.data.copy()
    if entry.options:
        new_data.update(entry.options)
    if entry.version > CONF_VERSION:
        _LOGGER.debug("Migration not needed")
        return True
    if entry.version == 4:
        return False
    if entry.version == 3:
        _LOGGER.debug(
            "Dropping account ID from config as this is no longer required")
        new_data.pop(CONF_ACCOUNT_ID, None)
        hass.config_entries.async_update_entry(
            entry, data=new_data, version=CONF_VERSION
        )
        return True
    return False
