"""Przebieg pojazdu – edytowalny z poziomu dashboardu lub automatyzacji."""

from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.const import UnitOfLength
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import VehicleConfigEntry
from .entity import VehicleEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VehicleConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([MileageNumber(entry.runtime_data, "mileage")])


class MileageNumber(VehicleEntity, NumberEntity):
    _attr_device_class = NumberDeviceClass.DISTANCE
    _attr_native_unit_of_measurement = UnitOfLength.KILOMETERS
    _attr_native_min_value = 0
    _attr_native_max_value = 2_000_000
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX

    @property
    def native_value(self) -> float | None:
        return self.vehicle.mileage

    async def async_set_native_value(self, value: float) -> None:
        await self.vehicle.async_set_mileage(int(value))
