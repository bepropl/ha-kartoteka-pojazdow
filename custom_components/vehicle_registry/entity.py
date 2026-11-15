"""Wspólna klasa bazowa encji pojazdu."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .calc import to_int
from .const import CONF_MAKE, CONF_MODEL, CONF_VIN, CONF_YEAR, DOMAIN
from .vehicle import Vehicle


class VehicleEntity(Entity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, vehicle: Vehicle, key: str) -> None:
        self.vehicle = vehicle
        self._attr_translation_key = key
        self._attr_unique_id = f"{vehicle.entry.entry_id}_{key}"

        cfg = vehicle.config
        year = to_int(cfg.get(CONF_YEAR))
        model = " ".join(str(x) for x in (cfg.get(CONF_MODEL), year) if x) or None
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, vehicle.entry.entry_id)},
            name=f"{vehicle.name} ({vehicle.plate})" if vehicle.plate else vehicle.name,
            manufacturer=cfg.get(CONF_MAKE) or None,
            model=model,
            serial_number=cfg.get(CONF_VIN) or None,
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self.vehicle.async_add_listener(self.async_write_ha_state))
