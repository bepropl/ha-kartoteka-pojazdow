"""Przyciski: przegląd wykonany, badanie wykonane, odnowienie polis."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import VehicleConfigEntry, calc
from .const import CONF_AC_DATE, MAINTENANCE_ITEMS
from .entity import VehicleEntity
from .vehicle import Vehicle


@dataclass(frozen=True, kw_only=True)
class VehicleButtonDescription(ButtonEntityDescription):
    press_fn: Callable[[Vehicle], Awaitable[None]]
    exists_fn: Callable[[dict[str, Any]], bool] = lambda cfg: True


BUTTONS: tuple[VehicleButtonDescription, ...] = (
    VehicleButtonDescription(key="service_done", press_fn=lambda v: v.async_service_done()),
    VehicleButtonDescription(
        key="inspection_done", press_fn=lambda v: v.async_inspection_done()
    ),
    VehicleButtonDescription(key="renew_oc", press_fn=lambda v: v.async_renew_oc()),
    VehicleButtonDescription(
        key="renew_ac",
        press_fn=lambda v: v.async_renew_ac(),
        exists_fn=lambda cfg: bool(cfg.get(CONF_AC_DATE)),
    ),
)


def _item_button(item: str) -> VehicleButtonDescription:
    return VehicleButtonDescription(
        key=f"{item}_done",
        press_fn=lambda v: v.async_item_done(item),
        exists_fn=lambda cfg: calc.item_enabled(cfg, item),
    )


BUTTONS += tuple(_item_button(item) for item in MAINTENANCE_ITEMS)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VehicleConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    vehicle = entry.runtime_data
    async_add_entities(
        VehicleButton(vehicle, desc) for desc in BUTTONS if desc.exists_fn(vehicle.config)
    )


class VehicleButton(VehicleEntity, ButtonEntity):
    entity_description: VehicleButtonDescription

    def __init__(self, vehicle: Vehicle, description: VehicleButtonDescription) -> None:
        super().__init__(vehicle, description.key)
        self.entity_description = description

    async def async_press(self) -> None:
        await self.entity_description.press_fn(self.vehicle)
