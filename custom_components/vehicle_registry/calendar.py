"""Kalendarz z terminami pojazdu (widoczny w zakładce Kalendarz HA)."""

from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import VehicleConfigEntry
from .const import KIND_AC, KIND_INSPECTION, KIND_OC, KIND_SERVICE
from .entity import VehicleEntity

LABELS = {
    "pl": {
        KIND_INSPECTION: "Badanie techniczne",
        KIND_OC: "Koniec OC",
        KIND_AC: "Koniec AC",
        KIND_SERVICE: "Przegląd serwisowy",
        "timing": "Wymiana rozrządu",
        "brake_fluid": "Wymiana płynu hamulcowego",
        "cabin_filter": "Wymiana filtra kabinowego",
        "battery": "Wymiana akumulatora",
        "warranty": "Koniec gwarancji",
        "assistance": "Koniec assistance",
        "leasing": "Koniec leasingu",
        "vignette_cz": "Koniec e-winiety CZ",
        "vignette_at": "Koniec winiety AT",
        "vignette_sk": "Koniec e-winiety SK",
    },
    "en": {
        KIND_INSPECTION: "Technical inspection",
        KIND_OC: "Liability insurance ends",
        KIND_AC: "Comprehensive insurance ends",
        KIND_SERVICE: "Service due",
        "timing": "Timing belt/chain replacement",
        "brake_fluid": "Brake fluid replacement",
        "cabin_filter": "Cabin filter replacement",
        "battery": "Battery replacement",
        "warranty": "Warranty ends",
        "assistance": "Assistance ends",
        "leasing": "Leasing ends",
        "vignette_cz": "CZ vignette ends",
        "vignette_at": "AT vignette ends",
        "vignette_sk": "SK vignette ends",
    },
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VehicleConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([VehicleCalendar(entry.runtime_data, "deadlines")])


class VehicleCalendar(VehicleEntity, CalendarEntity):
    def _events(self) -> list[CalendarEvent]:
        lang = "pl" if (self.hass.config.language or "").startswith("pl") else "en"
        labels = LABELS[lang]
        v = self.vehicle
        return [
            CalendarEvent(
                start=d.due,
                end=d.due + timedelta(days=1),
                summary=f"{v.name}: {labels[d.kind]}",
                description=v.plate or None,
                uid=f"{v.entry.entry_id}_{d.kind}",
            )
            for d in v.deadlines()
        ]

    @property
    def event(self) -> CalendarEvent | None:
        today = self.vehicle.today
        return next((e for e in self._events() if e.end > today), None)

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        start = dt_util.as_local(start_date).date()
        end = dt_util.as_local(end_date).date()
        return [e for e in self._events() if e.start <= end and e.end > start]
