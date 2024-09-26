"""DataUpdateCoordinator for integration_blueprint."""

from __future__ import annotations
import time
from datetime import timedelta, date, datetime
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
            update_interval=timedelta(minutes=20),
        )

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
        except ExpiredAccessTokenError as exception:
            if not token_refreshed:
                await self.client.api.refresh_login()
                await self._async_update_data(True)
            else:
                raise UpdateFailed(exception) from exception

    async def insert_statistics(self, start_date: date = None, end_date=date.today()):
        """Insert Anglian Water stats."""
        stat_id = f"{DOMAIN}:anglian_water_previous_consumption"
        cost_stat_id = f"{DOMAIN}:anglian_water_previous_costs"
        end_date = datetime.combine(end_date, datetime.min.time())
        if start_date is not None:
            # need to calculate the number of statistics to retrieve for last_stats
            timespan = datetime.now() - datetime.combine(
                start_date, datetime.min.time()
            )
            stat_count = (
                int(
                    round(
                        (((timespan.seconds / 3600) + (timespan.days * 24)) * 60) / 2, 0
                    )
                )
                + 1
            )
        else:
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
        if not last_stats:
            # First time lets insert last year of data
            if start_date is None:
                start_date = datetime.now()
            hourly_consumption_data = await self.client.get_usages(
                start=start_date - timedelta(days=365), end=end_date
            )
        else:
            # We will just use the most recent data
            if start_date is None:
                hourly_consumption_data = await self.client.get_usages(
                    start=datetime.fromtimestamp(last_stats.get("start")),
                    end=end_date,
                )
            else:
                hourly_consumption_data = await self.client.get_usages(
                    start=start_date
                    # request 6 hrs before as buffer for cost
                    - timedelta(hours=6),
                    end=end_date,
                )

        statistics = []
        cost_statistics = []
        cost = 0.0
        total_cost = last_cost_stats.get("sum", 0.0)
        if not isinstance(total_cost, float):
            total_cost = float(total_cost)
        previous_read = last_stats.get("sum", None)
        if previous_read is not None and not isinstance(previous_read, float):
            previous_read = float(previous_read)
        for reading in hourly_consumption_data["readings"]:
            start = dt_util.parse_datetime(
                reading["meterReadTimestamp"] + "+00:00")
            if is_dst(start):
                start = dt_util.parse_datetime(
                    reading["meterReadTimestamp"] + "+01:00")
            if last_stats is not None:
                if last_stats.get(
                    "start"
                ) is not None and start.timestamp() <= last_stats.get("start"):
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
            cost = (total_read - previous_read) * \
                self.client.current_tariff_rate
            total_cost += cost
            cost_statistics.append(
                StatisticData(
                    start=start - timedelta(hours=1), state=cost, sum=total_cost
                )
            )
            previous_read = int(reading["meterReadValue"]) / 1000

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
