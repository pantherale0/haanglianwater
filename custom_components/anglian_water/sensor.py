"""Sensor platform for anglian_water."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorDeviceClass,
)

from .const import DOMAIN
from .coordinator import AnglianWaterDataUpdateCoordinator
from .entity import AnglianWaterEntity

ENTITY_DESCRIPTIONS = (
    SensorEntityDescription(
        key="anglian_water_previous_consumption",
        name="Previous Consumption",
        icon="mdi:water",
        native_unit_of_measurement="m³",
        device_class=SensorDeviceClass.WATER,
    ),
    SensorEntityDescription(
        key="anglian_water_previous_cost",
        name="Previous Cost",
        icon="mdi:cash",
        native_unit_of_measurement="GBP",
        device_class=SensorDeviceClass.MONETARY,
    ),
)


async def async_setup_entry(hass, entry, async_add_devices):
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_devices(
        AnglianWaterSensor(
            coordinator=coordinator,
            entity_description=entity_description,
        )
        for entity_description in ENTITY_DESCRIPTIONS
    )


class AnglianWaterSensor(AnglianWaterEntity, SensorEntity):
    """anglian_water Sensor class."""

    def __init__(
        self,
        coordinator: AnglianWaterDataUpdateCoordinator,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator, entity_description.key)
        self.entity_description = entity_description

    @property
    def native_value(self) -> str:
        """Return the native value of the sensor."""
        if self.entity_description.key == "anglian_water_previous_cost":
            return self.coordinator.client.current_cost
        return self.coordinator.client.current_usage
