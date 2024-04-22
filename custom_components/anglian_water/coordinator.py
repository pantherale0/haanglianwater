"""DataUpdateCoordinator for integration_blueprint."""

from __future__ import annotations
import time
from datetime import timedelta, date, datetime

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.models import StatisticData, StatisticMetaData
from homeassistant.components.recorder.statistics import (
    async_add_external_statistics,
    get_last_statistics,
    statistic_during_period,
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
)

from .const import DOMAIN, LOGGER


def is_dst(utc_dt: datetime):
    """Check if time is in daylight savings time."""
    return bool(time.localtime(utc_dt.timestamp()).tm_isdst)


# https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
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
            update_interval=timedelta(minutes=20),
        )

    async def _async_update_data(self, token_refreshed: bool = False):
        """Update data via library."""
        try:
            await self.client.update()
            await self._insert_statistics()
        except InvalidUsernameError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except InvalidPasswordError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except UnknownEndpointError as exception:
            raise UpdateFailed(exception) from exception
        except ExpiredAccessTokenError as exception:
            if not token_refreshed:
                await self.client.api.refresh_login()
                await self._async_update_data(True)
            else:
                raise UpdateFailed(exception) from exception

    async def _insert_statistics(self):
        """Insert Anglian Water stats."""
        stat_id = f"{DOMAIN}:anglian_water_previous_consumption"
        cost_stat_id = f"{DOMAIN}:anglian_water_previous_costs"
        try:
            last_stats = await get_instance(self.hass).async_add_executor_job(
                get_last_statistics, self.hass, 1, stat_id, True, {"sum"}
            )
        except AttributeError:
            last_stats = None
        if not last_stats:
            # First time lets insert last year of data
            hourly_consumption_data = await self.client.get_usages(
                start=date.today() - timedelta(days=365),
                end=date.today(),
            )
            last_stats_time = None
        else:
            # We will just use the most recent data
            hourly_consumption_data = await self.client.get_usages(
                start=date.today() - timedelta(days=1), end=date.today()
            )
            start = dt_util.parse_datetime(
                hourly_consumption_data[0]["meterReadTimestamp"]
            )
            stat = await get_instance(self.hass).async_add_executor_job(
                statistic_during_period,
                self.hass,
                start,
                None,
                [stat_id],
                "hour",
                True,
            )
            last_stats_time = stat[stat_id][0]["start"]

        statistics = []
        cost_statistics = []
        cost = 0.0
        previous_read = None
        for reading in hourly_consumption_data["readings"]:
            start = dt_util.parse_datetime(reading["meterReadTimestamp"] + "+00:00")
            if is_dst(start):
                start = dt_util.parse_datetime(reading["meterReadTimestamp"] + "+01:00")
            if last_stats_time is not None and start <= last_stats_time:
                continue
            # remove an hour from the start time data rec for hour is actually for the last hour
            # eg received at 10am is for 9-10am and will show incorrectly in HASS energy dashboard
            total_read = int(reading["meterReadValue"]) / 1000
            statistics.append(
                StatisticData(
                    start=start - timedelta(hours=1),
                    state=reading["consumption"],
                    sum=total_read,
                )
            )
            if previous_read is None:
                previous_read = int(reading["meterReadValue"]) / 1000
                continue
            inst_cost = (total_read - previous_read) * self.client.current_tariff_rate
            cost += inst_cost
            cost_statistics.append(
                StatisticData(
                    start=start - timedelta(hours=1), state=inst_cost, sum=cost
                )
            )

        metadata_consumption = StatisticMetaData(
            has_mean=False,
            has_sum=True,
            name="Previous Water Consumption",
            source=DOMAIN,
            statistic_id=stat_id,
            unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        )
        metadata_cost = StatisticMetaData(
            has_mean=False,
            has_sum=True,
            name="Previous Water Cost",
            source=DOMAIN,
            statistic_id=cost_stat_id,
            unit_of_measurement="GBP",
        )
        async_add_external_statistics(self.hass, metadata_consumption, statistics)
        async_add_external_statistics(self.hass, metadata_cost, cost_statistics)
