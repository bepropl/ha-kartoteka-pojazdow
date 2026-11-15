"""Binary sensor "Wymaga uwagi" – włączony, gdy zbliża się lub minął jakiś termin."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import VehicleConfigEntry
from .entity import VehicleEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VehicleConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([AttentionBinarySensor(entry.runtime_data, "attention")])


class AttentionBinarySensor(VehicleEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    @property
    def is_on(self) -> bool:
        return bool(self.vehicle.attention())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"issues": self.vehicle.attention(), "plate": self.vehicle.plate}
