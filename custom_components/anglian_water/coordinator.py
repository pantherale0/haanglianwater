"""DataUpdateCoordinator for integration_blueprint."""

from __future__ import annotations
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.exceptions import ConfigEntryAuthFailed
from pyanglianwater import AnglianWater
from pyanglianwater.exceptions import (
    InvalidPasswordError,
    InvalidUsernameError,
    UnknownEndpointError,
    ExpiredAccessTokenError,
    ServiceUnavailableError,
    InvalidAccountIdError
)

from .const import DOMAIN, LOGGER


class AnglianWaterDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        client: AnglianWater,
    ) -> None:
        """Initialize."""
        self.client = client
        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=30),
        )

    async def _async_update_data(self, token_refreshed: bool = False):
        """Update data via library."""
        try:
            await self.client.update()
        except InvalidUsernameError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except InvalidPasswordError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except UnknownEndpointError as exception:
            raise UpdateFailed(exception) from exception
        except ServiceUnavailableError as exception:
            raise UpdateFailed(exception) from exception
        except InvalidAccountIdError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except ExpiredAccessTokenError as exception:
            # No need to retry here, because module already refreshes the token
            # This error is something different
            raise UpdateFailed(exception) from exception
