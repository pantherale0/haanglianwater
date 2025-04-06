"""DataUpdateCoordinator for integration_blueprint."""

from __future__ import annotations
import time
from datetime import timedelta, datetime
from operator import itemgetter

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.models import StatisticData, StatisticMetaData
from homeassistant.components.recorder.statistics import (
    async_import_statistics,
    async_add_external_statistics,
    get_last_statistics,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import UnitOfVolume
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.util import dt as dt_util
from pyanglianwater import AnglianWater
from pyanglianwater.exceptions import (
    InvalidPasswordError,
    InvalidUsernameError,
    UnknownEndpointError,
    ExpiredAccessTokenError,
    ServiceUnavailableError,
    InvalidAccountIdError
)

from .const import DOMAIN, LOGGER, CONF_VERSION


def is_dst(utc_dt: datetime):
    """Check if time is in daylight savings time."""
    return bool(time.localtime(utc_dt.timestamp()).tm_isdst)


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
            update_interval=timedelta(hours=6),
        )

    @property
    def get_yesterday_reads(self) -> list:
        """Retrieve yesterday's meter readings."""
        yesterday = datetime.now() - timedelta(days=1)
        yesterday = dt_util.as_local(yesterday)
        yesterday = yesterday.replace(
            hour=0, minute=0, second=0, microsecond=0)
        output = []
        for reading in self.client.current_readings:
            if dt_util.parse_datetime(reading["date"]).date() == yesterday.date():
                output.append(reading["meters"][0])
        return output

    @property
    def get_yesterday_cost(self) -> float:
        """Return the cost of water usage yesterday."""
        output = 0.0
        for reading in self.get_yesterday_reads:
            output += (reading["consumption"]/1000) * \
                self.client.current_tariff_rate
        return output

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
