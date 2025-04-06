"""DataUpdateCoordinator for integration_blueprint."""

from __future__ import annotations
import time
from datetime import timedelta, datetime
from operator import itemgetter

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.models import StatisticData, StatisticMetaData
from homeassistant.components.recorder.statistics import (
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
            await self.insert_statistics()
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
            if not token_refreshed:
                await self.client.api.token_refresh()
                await self._async_update_data(True)
            else:
                raise UpdateFailed(exception) from exception

    async def insert_statistics(self):
        """Insert Anglian Water stats."""
        stat_id = f"{DOMAIN}:anglian_water_previous_consumption"
        cost_stat_id = f"{DOMAIN}:anglian_water_previous_costs"
        stat_count = 1
        try:
            last_stats = await get_instance(self.hass).async_add_executor_job(
                get_last_statistics, self.hass, stat_count, stat_id, True, {
                    "sum"}
            )
            last_cost_stats = await get_instance(self.hass).async_add_executor_job(
                get_last_statistics, self.hass, stat_count, cost_stat_id, True, {
                    "sum"}
            )
            if len(last_stats.get(stat_id, [])) > 0:
                last_stats = last_stats[stat_id]
                last_stats = sorted(last_stats, key=itemgetter("start"), reverse=False)[
                    0
                ]
            if len(last_cost_stats.get(cost_stat_id, [])) > 0:
                last_cost_stats = last_cost_stats[cost_stat_id]
                last_cost_stats = sorted(
                    last_cost_stats, key=itemgetter("start"), reverse=False
                )[0]
        except AttributeError:
            last_stats = None
        hourly_consumption_data = self.client.current_readings

        statistics = []
        cost_statistics = []
        cost = 0.0
        total_cost = last_cost_stats.get("sum", 0.0)
        if not isinstance(total_cost, float):
            total_cost = float(total_cost)
        previous_read = last_stats.get("sum", None)
        if previous_read is not None and not isinstance(previous_read, float):
            previous_read = float(previous_read)
        for reading in hourly_consumption_data:
            start = dt_util.parse_datetime(
                reading["date"]).replace(tzinfo=dt_util.get_time_zone("Europe/London"))
            if is_dst(start):
                start = dt_util.parse_datetime(
                    reading["date"]).replace(tzinfo=dt_util.get_time_zone("Europe/London"))
            if last_stats is not None:
                if last_stats.get(
                    "start"
                ) is not None and start.timestamp() <= last_stats.get("start"):
                    continue
            # remove an hour from the start time data rec for hour is actually for the last hour
            # eg received at 10am is for 9-10am and will show incorrectly in HASS energy dashboard
            total_read = reading["meters"][0]["read"]
            statistics.append(
                StatisticData(
                    start=start - timedelta(hours=1),
                    state=reading["meters"][0]["consumption"],
                    sum=total_read,
                )
            )
            if previous_read is None:
                previous_read = reading["meters"][0]["read"]
                continue
            cost = (total_read - previous_read) * \
                self.client.current_tariff_rate
            total_cost += cost
            cost_statistics.append(
                StatisticData(
                    start=start - timedelta(hours=1), state=cost, sum=total_cost
                )
            )
            previous_read = reading["meters"][0]["read"]

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
        async_add_external_statistics(
            self.hass, metadata_consumption, statistics)
        async_add_external_statistics(
            self.hass, metadata_cost, cost_statistics)
        if self.config_entry.version < CONF_VERSION:
            self.hass.config_entries.async_update_entry(
                self.config_entry, version=CONF_VERSION
            )
