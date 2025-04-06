"""AnglianWaterEntity class."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.const import UnitOfVolume
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.recorder.statistics import (
    async_import_statistics
)
from homeassistant.components.recorder.models import StatisticMetaData, StatisticData
from homeassistant.util import dt as dt_util
from pyanglianwater import SmartMeter

from .const import DOMAIN, NAME, VERSION
from .coordinator import AnglianWaterDataUpdateCoordinator


class AnglianWaterEntity(CoordinatorEntity):
    """AnglianWaterEntity class."""

    def __init__(
        self, coordinator: AnglianWaterDataUpdateCoordinator, entity: str, meter: str
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
        coordinator.client.register_callback(self.schedule_update_ha_state)
        coordinator.client.register_callback(self._update_statistics)

    def _update_statistics(self):
        """Update statistics for this meter."""
        for reading in self.meter.readings:
            if self.entity_description.key == "anglian_water_latest_consumption":
                async_import_statistics(
                    self.hass,
                    metadata=StatisticMetaData(
                        source="recorder",
                        statistic_id=self.entity_id,
                        name=self.name,
                        has_mean=False,
                        has_sum=True,
                        unit_of_measurement=UnitOfVolume.LITERS
                    ),
                    statistics=[StatisticData(
                        start=dt_util.as_local(dt_util.parse_datetime(
                            reading["read_at"])) - timedelta(hours=1),
                        state=reading["consumption"],
                        sum=reading["read"]*1000,
                    )]
                )
            if self.entity_description.key == "anglian_water_latest_cost":
                stat_start = dt_util.as_local(dt_util.parse_datetime(
                    reading["read_at"])) - timedelta(hours=1)
                if stat_start.hour == 0:
                    offset_cost = self.coordinator.client.current_tariff_service / 365
                else:
                    offset_cost = 0
                async_import_statistics(
                    self.hass,
                    metadata=StatisticMetaData(
                        source="recorder",
                        statistic_id=self.entity_id,
                        name=self.name,
                        has_mean=False,
                        has_sum=True,
                        unit_of_measurement="GBP"
                    ),
                    statistics=[StatisticData(
                        start=stat_start,
                        state=reading["consumption"] *
                        self.meter.tariff_rate / 1000 + offset_cost,
                        sum=reading["read"] *
                        self.meter.tariff_rate + offset_cost,
                    )]
                )

    @property
    def meter(self) -> SmartMeter:
        """Return the meter object."""
        return self.coordinator.client.meters[self._meter_serial]
