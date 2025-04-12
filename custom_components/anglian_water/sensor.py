"""Sensor platform for anglian_water."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorDeviceClass,
    SensorStateClass
)

from homeassistant.const import (
    UnitOfVolume
)

# from homeassistant.helpers import entity_platform
from .const import DOMAIN, CONF_METERS, CONF_INITIAL_READ
from .coordinator import AnglianWaterDataUpdateCoordinator
from .entity import AnglianWaterEntity


@dataclass(frozen=True, kw_only=True)
class AnglianWaterSensorEntityDescription(SensorEntityDescription):
    """Describes AnglianWater sensor entity."""

    key: str
    value_fn: Callable[[AnglianWaterEntity],
                       float] | None = None
    name_fn: Callable[[AnglianWaterEntity], str] | None = None


ENTITY_DESCRIPTIONS: dict[str, AnglianWaterSensorEntityDescription] = {
    "anglian_water_previous_consumption": AnglianWaterSensorEntityDescription(
        key="anglian_water_previous_consumption",
        name_fn=lambda entity: f"{entity.meter.serial_number} Yesterday Consumption",
        icon="mdi:water",
        native_unit_of_measurement="L",
        device_class=SensorDeviceClass.WATER,
        value_fn=lambda entity: entity.meter.get_yesterday_consumption
    ),
    "anglian_water_previous_cost": AnglianWaterSensorEntityDescription(
        key="anglian_water_previous_cost",
        name_fn=lambda entity: f"{entity.meter.serial_number} Yesterday Cost",
        icon="mdi:cash",
        native_unit_of_measurement="GBP",
        device_class=SensorDeviceClass.MONETARY,
        value_fn=lambda entity: entity.meter.get_yesterday_cost,
    ),
    "anglian_water_latest_reading": AnglianWaterSensorEntityDescription(
        key="anglian_water_latest_reading",
        name_fn=lambda entity: f"{entity.meter.serial_number} Latest Reading",
        icon="mdi:water",
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        device_class=SensorDeviceClass.WATER,
        value_fn=lambda entity: entity.meter.latest_read-entity._meter_initial_read,
        state_class=SensorStateClass.TOTAL_INCREASING
    ),
    "anglian_water_latest_cost": AnglianWaterSensorEntityDescription(
        key="anglian_water_latest_cost",
        name_fn=lambda entity: f"{entity.meter.serial_number} Latest Cost",
        icon="mdi:cash",
        native_unit_of_measurement="GBP",
        device_class=SensorDeviceClass.MONETARY,
        value_fn=lambda entity: (
            entity.meter.latest_read-entity._meter_initial_read) * entity.meter.tariff_rate,
        state_class=SensorStateClass.TOTAL_INCREASING
    ),
}


async def async_setup_entry(hass, entry, async_add_devices):
    """Set up the sensor platform."""
    coordinator: AnglianWaterDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    for meter in entry.data[CONF_METERS]:
        async_add_devices(
            GenericSensor(
                coordinator=coordinator,
                entity_description=entity_description,
                meter_serial=meter,
                meter_initial_read=entry.data[CONF_METERS][meter][CONF_INITIAL_READ],
            )
            for entity_description in ENTITY_DESCRIPTIONS.values()
        )

    # platform = entity_platform.async_get_current_platform()
    # platform.async_register_entity_service(
    #     "migrate_statistics",
    #     {},
    #     "migrate_statistics",
    # )


class GenericSensor(AnglianWaterEntity, SensorEntity):
    """anglian_water Sensor class."""

    def __init__(
        self,
        coordinator: AnglianWaterDataUpdateCoordinator,
        entity_description: AnglianWaterSensorEntityDescription,
        meter_serial: str,
        meter_initial_read: float,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator, entity_description.key, meter_serial, meter_initial_read)
        self.entity_description = entity_description

    @property
    def name(self) -> str:
        """Return name of entity."""
        return self.entity_description.name_fn(self)

    @property
    def native_value(self):
        """Return the native value of the entity."""
        return self.entity_description.value_fn(self)

    @property
    def device_class(self):
        """Return device class."""
        return self.entity_description.device_class
