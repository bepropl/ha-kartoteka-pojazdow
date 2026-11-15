"""Sensory: terminy, km do przeglądu, numer rejestracyjny."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfLength
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import VehicleConfigEntry, calc
from .const import (
    CONF_AC_DATE,
    CONF_FUEL,
    CONF_NOTES,
    CONF_OC_INSURER,
    CONF_OC_POLICY,
    CONF_VIN,
    EXTRA_DATES,
    MAINTENANCE_ITEMS,
    item_key,
)
from .entity import VehicleEntity
from .vehicle import Vehicle


def _days(getter: Callable[[Vehicle], date | None]) -> Callable[[Vehicle], dict[str, Any]]:
    return lambda v: {"days_left": v.days_left(getter(v))}


def _oc_attrs(v: Vehicle) -> dict[str, Any]:
    cfg = v.config
    return {
        "days_left": v.days_left(v.oc_due),
        "insurer": cfg.get(CONF_OC_INSURER),
        "policy_number": cfg.get(CONF_OC_POLICY),
    }


def _service_attrs(v: Vehicle) -> dict[str, Any]:
    return {
        "days_left": v.days_left(v.next_service_date),
        "due_km": v.next_service_km,
        "km_left": v.km_to_service,
    }


def _next_deadline(v: Vehicle) -> date | None:
    items = v.deadlines()
    return items[0].due if items else None


def _next_deadline_attrs(v: Vehicle) -> dict[str, Any]:
    items = v.deadlines()
    if not items:
        return {}
    first = items[0]
    return {
        "kind": first.kind,
        "days_left": first.days_left,
        "all": [
            {"kind": d.kind, "due": d.due.isoformat(), "days_left": d.days_left}
            for d in items
        ],
    }


def _plate_attrs(v: Vehicle) -> dict[str, Any]:
    cfg = v.config
    return {"vin": cfg.get(CONF_VIN), "fuel": cfg.get(CONF_FUEL), "notes": cfg.get(CONF_NOTES)}


@dataclass(frozen=True, kw_only=True)
class VehicleSensorDescription(SensorEntityDescription):
    value_fn: Callable[[Vehicle], Any]
    attrs_fn: Callable[[Vehicle], dict[str, Any]] | None = None
    exists_fn: Callable[[dict[str, Any]], bool] = lambda cfg: True


SENSORS: tuple[VehicleSensorDescription, ...] = (
    VehicleSensorDescription(
        key="next_deadline",
        device_class=SensorDeviceClass.DATE,
        value_fn=_next_deadline,
        attrs_fn=_next_deadline_attrs,
    ),
    VehicleSensorDescription(
        key="inspection",
        device_class=SensorDeviceClass.DATE,
        value_fn=lambda v: v.inspection_due,
        attrs_fn=_days(lambda v: v.inspection_due),
    ),
    VehicleSensorDescription(
        key="oc",
        device_class=SensorDeviceClass.DATE,
        value_fn=lambda v: v.oc_due,
        attrs_fn=_oc_attrs,
    ),
    VehicleSensorDescription(
        key="ac",
        device_class=SensorDeviceClass.DATE,
        value_fn=lambda v: v.ac_due,
        attrs_fn=_days(lambda v: v.ac_due),
        exists_fn=lambda cfg: bool(cfg.get(CONF_AC_DATE)),
    ),
    VehicleSensorDescription(
        key="next_service",
        device_class=SensorDeviceClass.DATE,
        value_fn=lambda v: v.next_service_date,
        attrs_fn=_service_attrs,
    ),
    VehicleSensorDescription(
        key="service_km_left",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        suggested_display_precision=0,
        value_fn=lambda v: v.km_to_service,
    ),
    VehicleSensorDescription(
        key="plate",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda v: v.plate or None,
        attrs_fn=_plate_attrs,
    ),
)


def _item_sensors(item: str) -> tuple[VehicleSensorDescription, ...]:
    """Data następnej wymiany + km do wymiany dla elementu eksploatacyjnego."""

    def attrs(v: Vehicle) -> dict[str, Any]:
        cfg = v.config
        return {
            "days_left": v.days_left(v.item_due_date(item)),
            "due_km": v.item_due_km(item),
            "km_left": v.item_km_left(item),
            "last_date": cfg.get(item_key(item, "last_date")),
            "last_km": cfg.get(item_key(item, "last_km")),
        }

    return (
        VehicleSensorDescription(
            key=item,
            device_class=SensorDeviceClass.DATE,
            value_fn=lambda v: v.item_due_date(item),
            attrs_fn=attrs,
            exists_fn=lambda cfg: calc.item_due_date(cfg, item) is not None,
        ),
        VehicleSensorDescription(
            key=f"{item}_km_left",
            device_class=SensorDeviceClass.DISTANCE,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfLength.KILOMETERS,
            suggested_display_precision=0,
            value_fn=lambda v: v.item_km_left(item),
            exists_fn=lambda cfg: calc.item_due_km(cfg, item) is not None,
        ),
    )


def _extra_sensor(kind: str) -> VehicleSensorDescription:
    return VehicleSensorDescription(
        key=kind,
        device_class=SensorDeviceClass.DATE,
        value_fn=lambda v: v.extra_date(kind),
        attrs_fn=_days(lambda v: v.extra_date(kind)),
        exists_fn=lambda cfg: calc.extra_date(cfg, kind) is not None,
    )


ALL_SENSORS: tuple[VehicleSensorDescription, ...] = (
    SENSORS
    + tuple(d for item in MAINTENANCE_ITEMS for d in _item_sensors(item))
    + tuple(_extra_sensor(kind) for kind in EXTRA_DATES)
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VehicleConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    vehicle = entry.runtime_data
    async_add_entities(
        VehicleSensor(vehicle, desc)
        for desc in ALL_SENSORS
        if desc.exists_fn(vehicle.config)
    )


class VehicleSensor(VehicleEntity, SensorEntity):
    entity_description: VehicleSensorDescription

    def __init__(self, vehicle: Vehicle, description: VehicleSensorDescription) -> None:
        super().__init__(vehicle, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.vehicle)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        fn = self.entity_description.attrs_fn
        return fn(self.vehicle) if fn else None
