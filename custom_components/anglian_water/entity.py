"""AnglianWaterEntity class."""

from __future__ import annotations
import logging
from datetime import timedelta

from homeassistant.const import MATCH_ALL
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.models import StatisticData, StatisticMetaData
from homeassistant.components.recorder.statistics import (
    async_import_statistics,
    get_last_statistics
)
from homeassistant.util import dt as dt_util
from pyanglianwater import SmartMeter

from .const import DOMAIN, NAME, VERSION
from .coordinator import AnglianWaterDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class AnglianWaterEntity(CoordinatorEntity):
    """AnglianWaterEntity class."""

    _unrecorded_attributes = frozenset({MATCH_ALL})

    def __init__(
        self, coordinator: AnglianWaterDataUpdateCoordinator, entity: str, meter: str, meter_initial_read: float
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._meter_serial = meter
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{entity}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            name=meter,
            model=VERSION,
            manufacturer=NAME,
            serial_number=meter
        )
        self._meter_initial_read = meter_initial_read
        coordinator.client.register_callback(self.schedule_update_ha_state)
        coordinator.client.register_callback(self._update_statistics)

    async def _update_statistics(self):
        """Update statistics for this meter."""
        _LOGGER.debug("Updating statistics for %s", self.entity_id)
        metadata = StatisticMetaData(
            source="recorder",
            statistic_id=self.entity_id,
            name=self.name,
            has_mean=False,
            has_sum=True,
            unit_of_measurement=self.unit_of_measurement
        )
        stats = await get_instance(self.hass).async_add_executor_job(
            get_last_statistics, self.hass, 1, self.entity_id, True, {
                "sum", "state"}
        )
        latest_stat = None
        if self.entity_id in stats:
            stats = stats[self.entity_id]
            if len(stats) > 0:
                latest_stat = stats[0]["sum"]
        for reading in self.meter.readings:
            stat_start = dt_util.as_local(dt_util.parse_datetime(
                reading["read_at"])) - timedelta(hours=1)
            if self.entity_description.key == "anglian_water_latest_reading":
                if latest_stat is not None:
                    if latest_stat > reading["read"]-self._meter_initial_read:
                        continue
                async_import_statistics(
                    self.hass,
                    metadata=metadata,
                    statistics=[StatisticData(
                        start=stat_start,
                        state=reading["read"]-self._meter_initial_read,
                        sum=reading["read"]-self._meter_initial_read
                    )]
                )
            if self.entity_description.key == "anglian_water_latest_cost":
                if latest_stat is not None:
                    if latest_stat > (reading["read"]-self._meter_initial_read) * self.meter.tariff_rate:
                        continue
                async_import_statistics(
                    self.hass,
                    metadata=metadata,
                    statistics=[StatisticData(
                        start=stat_start,
                        state=(
                            reading["read"]-self._meter_initial_read) * self.meter.tariff_rate,
                        sum=(reading["read"]-self._meter_initial_read) *
                        self.meter.tariff_rate
                    )]
                )

    # async def migrate_statistics(self):
    #     """Migrate statistics from external to internal."""
    #     timespan = datetime.now() - timedelta(days=365*10)
    #     timespan = datetime.now() - datetime.combine(
    #         timespan, datetime.min.time()
    #     )
    #     stat_count = (
    #         int(
    #             round(
    #                 (((timespan.seconds / 3600) + (timespan.days * 24)) * 60) / 2, 0
    #             )
    #         )
    #         + 1
    #     )
    #     try:
    #         if self.entity_description.key == "anglian_water_latest_consumption":
    #             stat_id = f"{DOMAIN}:anglian_water_previous_consumption"
    #             stats = await get_instance(self.hass).async_add_executor_job(
    #                 get_last_statistics, self.hass, stat_count, stat_id, True, {
    #                     "sum", "state"}
    #             )
    #             metadata = StatisticMetaData(
    #                 source="recorder",
    #                 statistic_id=self.entity_id,
    #                 name=self.name,
    #                 has_mean=False,
    #                 has_sum=True,
    #                 unit_of_measurement=UnitOfVolume.LITERS
    #             )
    #         elif self.entity_description.key == "anglian_water_latest_cost":
    #             stat_id = f"{DOMAIN}:anglian_water_previous_costs"
    #             stats = await get_instance(self.hass).async_add_executor_job(
    #                 get_last_statistics, self.hass, stat_count, stat_id, True, {
    #                     "sum", "state"}
    #             )
    #             metadata = StatisticMetaData(
    #                 source="recorder",
    #                 statistic_id=self.entity_id,
    #                 name=self.name,
    #                 has_mean=False,
    #                 has_sum=True,
    #                 unit_of_measurement="GBP"
    #             )
    #         else:
    #             return None
    #         if len(stats) > 0:
    #             for stat in stats[stat_id]:
    #                 async_import_statistics(
    #                     self.hass,
    #                     metadata=metadata,
    #                     statistics=[StatisticData(
    #                         start=dt_util.as_local(datetime.fromtimestamp(
    #                             stat["start"])),
    #                         end=dt_util.as_local(datetime.fromtimestamp(
    #                             stat["end"])),
    #                         state=stat["state"],
    #                         sum=stat["sum"]
    #                     )]
    #                 )
    #     except Exception as exception:
    #         _LOGGER.error("Stats migration failed: %s", exception)
    #         return False

    @property
    def meter(self) -> SmartMeter:
        """Return the meter object."""
        return self.coordinator.client.meters[self._meter_serial]
