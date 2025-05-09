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
DELAY_BUFFER_HOURS = 25


class AnglianWaterEntity(CoordinatorEntity):
    """AnglianWaterEntity class."""

    _unrecorded_attributes = frozenset({MATCH_ALL})

    def __init__(
        self,
        coordinator: AnglianWaterDataUpdateCoordinator,
        entity: str,
        meter: SmartMeter
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self.meter = meter
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{entity}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            name=meter.serial_number,
            model=VERSION,
            manufacturer=NAME,
            serial_number=meter.serial_number
        )

    async def async_added_to_hass(self):
        """Actions to execute after the entity has been added into Home Assistant."""
        self.coordinator.client.register_callback(
            self.async_schedule_update_ha_state)
        if "latest" in self.entity_description.key:
            self.coordinator.client.register_callback(self._update_statistics)
            await self._update_statistics()

    async def _update_statistics(self):
        """Update statistics for this meter, handling delayed readings and offset."""
        _LOGGER.debug(
            "Updating statistics for %s (handling delay/offset)", self.entity_id)

        # Sort readings by timestamp to ensure processing order
        # Use get() for safety in case 'read_at' key is missing for some reason
        sorted_readings = sorted(self.meter.readings, key=lambda x: dt_util.parse_datetime(
            x.get("read_at")))

        if not sorted_readings:
            _LOGGER.debug("No readings available for %s", self.entity_id)
            return  # Nothing to process

        metadata = StatisticMetaData(
            source="recorder",
            statistic_id=self.entity_id,
            name=self.name,
            has_mean=False,
            has_sum=True,  # We are providing a cumulative sum
            unit_of_measurement=self.unit_of_measurement
        )

        new_statistic_data = []

        # Get the last known cumulative sum and timestamp from the recorder
        last_stats = await get_instance(self.hass).async_add_executor_job(
            get_last_statistics, self.hass, 1, self.entity_id, True, {
                "sum", "state"}
        )
        last_statistic_data = last_stats.get(self.entity_id)
        if isinstance(last_statistic_data, list) and len(last_statistic_data) > 0:
            last_statistic_data = last_statistic_data[0]

        last_recorded_sum = last_statistic_data.get(
            "sum", None) if last_statistic_data else None
        last_statistic_time = last_statistic_data.get(
            "start", None) if last_statistic_data else None  # Timestamp in UTC seconds

        # --- Calculate the cumulative offset ---
        cumulative_offset = 0.0
        first_new_reading_value = None
        filtered_readings = []

        # Find the first reading that is newer than the last recorded statistic
        if last_statistic_time is not None:
            last_statistic_dt_utc = dt_util.utc_from_timestamp(
                last_statistic_time)
            # Use a small tolerance (e.g., 1 second) to handle potential floating point issues or identical timestamps
            filtered_readings = [
                r for r in sorted_readings
                if dt_util.as_utc(dt_util.as_local(dt_util.parse_datetime(r.get("read_at")))) > last_statistic_dt_utc + timedelta(seconds=1)
            ]
        else:
            # No previous statistics, all readings are potentially new
            filtered_readings = sorted_readings

        if filtered_readings:
            first_new_reading = filtered_readings[0]
            # Determine the raw cumulative value of the first new reading based on the key
            if self.entity_description.key == "anglian_water_latest_reading":
                # Assuming reading["read"] is the cumulative water meter reading in Litres
                first_new_reading_value = first_new_reading.get(
                    "read", 0.0) / 1000.0  # Convert to m3
            elif self.entity_description.key == "anglian_water_latest_cost":
                # Assuming reading["read"] is the cumulative value that cost is based on (e.g., m3)
                # and the tariff rate is applied to the cumulative value for the sum field
                first_new_reading_value = first_new_reading.get(
                    "read", 0.0) * self.meter.tariff_rate
            else:
                _LOGGER.warning(
                    "Unknown entity description key for offset calculation: %s", self.entity_description.key)
                # Cannot calculate offset reliably, proceed assuming offset is 0 or handle error

            if last_recorded_sum is not None and first_new_reading_value is not None:
                # Calculate the offset needed to make the first new reading's value
                # continue seamlessly from the last recorded sum.
                cumulative_offset = last_recorded_sum - first_new_reading_value
                _LOGGER.debug(
                    "Calculated cumulative offset for %s: last_sum=%.4f, first_new_read_value=%.4f, offset=%.4f",
                    self.entity_id, last_recorded_sum, first_new_reading_value, cumulative_offset
                )
            elif first_new_reading_value is not None:
                # This is likely the very first run, or previous stats were cleared.
                # The first reading's value becomes the starting point for the cumulative sum (offset is 0).
                _LOGGER.debug(
                    "No previous statistics found for %s. Starting cumulative sum from first reading value.", self.entity_id)
                cumulative_offset = 0.0
                # The first reading's value will be `raw_read_value + cumulative_offset = raw_read_value`.

        if not filtered_readings:
            _LOGGER.debug(
                "No new readings found after filtering for %s", self.entity_id)
            return  # Nothing new to process

        # --- Process filtered readings and apply recency filter ---
        now_local = dt_util.now()
        # Readings newer than this cutoff will be skipped
        recency_cutoff_dt = now_local - timedelta(hours=DELAY_BUFFER_HOURS)
        _LOGGER.debug(
            "Recency cutoff for processing readings: before %s (Local)", recency_cutoff_dt)

        for reading in filtered_readings:
            try:
                reading_dt_local = dt_util.as_local(
                    dt_util.parse_datetime(reading.get("read_at")))
            except (ValueError, TypeError):
                _LOGGER.warning(
                    "Could not parse reading timestamp: %s", reading.get("read_at"))
                continue  # Skip this reading

            # Apply Recency Filter: Skip this reading and all subsequent ones if it's too recent
            if reading_dt_local >= recency_cutoff_dt:
                _LOGGER.debug(
                    "Skipping reading at %s (Local) due to recency cutoff %s (Local). All subsequent readings also skipped.",
                    reading_dt_local, recency_cutoff_dt
                )
                break  # Readings are sorted, so we can stop

            # Keep the original stat_start calculation logic if the user insists,
            # although using reading_dt_local directly might be more standard.
            # stat_start = reading_dt_local - timedelta(hours=1)
            stat_start = reading_dt_local  # Use the reading time directly, or adjust as needed

            # Calculate 'state' based on consumption (as in original code)
            if self.entity_description.key == "anglian_water_latest_reading":
                state_value = reading.get("consumption", 0.0)/1000
            elif self.entity_description.key == "anglian_water_latest_cost":
                state_value = reading.get(
                    "consumption", 0.0) * (self.meter.tariff_rate / 1000.0)
            else:
                state_value = 0.0  # Should not happen

            # Get the raw cumulative value from the reading
            if self.entity_description.key == "anglian_water_latest_reading":
                raw_cumulative_value = reading.get(
                    "read", 0.0)
            elif self.entity_description.key == "anglian_water_latest_cost":
                raw_cumulative_value = reading.get(
                    "read", 0.0) * self.meter.tariff_rate
            else:
                raw_cumulative_value = 0.0  # Should not happen

            # Apply the calculated offset to the raw cumulative value
            corrected_cumulative_sum = raw_cumulative_value + cumulative_offset

            # Ensure the cumulative sum is monotonically increasing within the current batch being processed.
            # This handles potential minor glitches or out-of-order readings within the filtered batch.
            # Get the sum of the last statistic added *in this batch* (if any)
            last_added_sum_in_batch = new_statistic_data[-1]["sum"] if new_statistic_data else (
                last_recorded_sum if last_recorded_sum is not None else corrected_cumulative_sum)

            # If the corrected sum is less than the last sum we added (or the last recorded sum),
            # use the previous sum to ensure monotonicity. This might indicate a data issue or reset.
            # Note: This won't magically fix large jumps/dips from API side resets,
            # but prevents creating negative deltas within the batch itself.
            if corrected_cumulative_sum < last_added_sum_in_batch:
                _LOGGER.warning(
                    "Detected non-monotonic cumulative sum for %s at %s: %.4f < %.4f. Using previous sum.",
                    self.entity_id, reading_dt_local, corrected_cumulative_sum, last_added_sum_in_batch
                )
                corrected_cumulative_sum = last_added_sum_in_batch

            # Create the StatisticData entry
            # Note: Home Assistant prefers UTC timestamps for 'start'
            stat_start_utc = dt_util.as_utc(stat_start)

            new_statistic_data.append(StatisticData(
                start=stat_start_utc,
                state=state_value,  # Usage/cost since last reading
                # Cumulative total from the start (with offset)
                sum=corrected_cumulative_sum
            ))

        # The original code's incomplete day logic is removed as it doesn't fit the
        # per-reading cumulative + recency filter approach. The recency filter
        # effectively handles avoiding partial recent data.

        if new_statistic_data:
            # Import the generated statistics
            async_import_statistics(
                self.hass,
                metadata=metadata,
                statistics=new_statistic_data
            )
            _LOGGER.debug("Successfully imported %d statistics for %s", len(
                new_statistic_data), self.entity_id)
        else:
            _LOGGER.debug(
                "No new statistics to import after filtering and recency check for %s", self.entity_id)

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
