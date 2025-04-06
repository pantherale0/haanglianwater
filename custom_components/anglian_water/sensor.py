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
from .const import DOMAIN
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
    "anglian_water_latest_consumption": AnglianWaterSensorEntityDescription(
        key="anglian_water_latest_consumption",
        name_fn=lambda entity: f"{entity.meter.serial_number} Latest Consumption",
        icon="mdi:water",
        native_unit_of_measurement="L",
        device_class=SensorDeviceClass.WATER,
        value_fn=lambda entity: entity.meter.latest_consumption,
        state_class=SensorStateClass.TOTAL
    ),
    "anglian_water_latest_cost": AnglianWaterSensorEntityDescription(
        key="anglian_water_latest_cost",
        name_fn=lambda entity: f"{entity.meter.serial_number} Latest Cost",
        icon="mdi:cash",
        native_unit_of_measurement="GBP",
        device_class=SensorDeviceClass.MONETARY,
        value_fn=lambda entity: entity.meter.latest_consumption *
            (entity.meter.tariff_rate/1000) +
        (entity.coordinator.client.current_tariff_service / 365),
        state_class=SensorStateClass.TOTAL
    ),
}


async def async_setup_entry(hass, entry, async_add_devices):
    """Set up the sensor platform."""
    coordinator: AnglianWaterDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    for meter in coordinator.client.meters.values():
        async_add_devices(
            GenericSensor(
                coordinator=coordinator,
                entity_description=entity_description,
                meter_serial=meter.serial_number
            )
            for entity_description in ENTITY_DESCRIPTIONS.values()
        )


class GenericSensor(AnglianWaterEntity, SensorEntity):
    """anglian_water Sensor class."""

    def __init__(
        self,
        coordinator: AnglianWaterDataUpdateCoordinator,
        entity_description: AnglianWaterSensorEntityDescription,
        meter_serial: str
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator, entity_description.key, meter_serial)
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
