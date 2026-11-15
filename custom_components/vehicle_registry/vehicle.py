"""Model pojazdu: odczyt konfiguracji, terminy i akcje (przegląd wykonany itp.)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.util import dt as dt_util

from . import calc
from .const import (
    CONF_AC_DATE,
    CONF_INSPECTION_DATE,
    CONF_INSPECTION_INTERVAL,
    CONF_LAST_SERVICE_DATE,
    CONF_LAST_SERVICE_KM,
    CONF_MILEAGE,
    CONF_NAME,
    CONF_OC_DATE,
    CONF_PLATE,
    DEFAULTS,
    item_key,
)


class Vehicle:
    """Jeden pojazd = jeden wpis konfiguracji."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.internal_update = False
        self._listeners: list[Callable[[], None]] = []

    # --- odczyt -------------------------------------------------------------

    @property
    def config(self) -> dict[str, Any]:
        return {**DEFAULTS, **self.entry.data, **self.entry.options}

    @property
    def name(self) -> str:
        return self.config.get(CONF_NAME) or "Pojazd"

    @property
    def plate(self) -> str:
        return self.config.get(CONF_PLATE) or ""

    @property
    def today(self) -> date:
        return dt_util.now().date()

    @property
    def mileage(self) -> int | None:
        return calc.to_int(self.config.get(CONF_MILEAGE))

    @property
    def inspection_due(self) -> date | None:
        return calc.parse_date(self.config.get(CONF_INSPECTION_DATE))

    @property
    def oc_due(self) -> date | None:
        return calc.parse_date(self.config.get(CONF_OC_DATE))

    @property
    def ac_due(self) -> date | None:
        return calc.parse_date(self.config.get(CONF_AC_DATE))

    @property
    def next_service_date(self) -> date | None:
        return calc.next_service_date(self.config)

    @property
    def next_service_km(self) -> int | None:
        return calc.next_service_km(self.config)

    @property
    def km_to_service(self) -> int | None:
        return calc.km_to_service(self.config)

    def days_left(self, due: date | None) -> int | None:
        return None if due is None else (due - self.today).days

    def deadlines(self) -> list[calc.Deadline]:
        return calc.deadlines(self.config, self.today)

    def attention(self) -> list[dict[str, Any]]:
        return calc.attention(self.config, self.today)

    # --- powiadamianie encji ----------------------------------------------

    @callback
    def async_add_listener(self, update: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(update)

        @callback
        def remove() -> None:
            self._listeners.remove(update)

        return remove

    @callback
    def async_notify(self) -> None:
        for update in list(self._listeners):
            update()

    # --- akcje --------------------------------------------------------------

    async def async_update_values(self, **changes: Any) -> None:
        """Zapisz zmiany bez przeładowania integracji."""
        self.internal_update = True
        self.hass.config_entries.async_update_entry(
            self.entry, options={**self.entry.options, **changes}
        )
        self.async_notify()

    async def async_set_mileage(self, km: int) -> None:
        await self.async_update_values(**{CONF_MILEAGE: int(km)})

    async def async_service_done(self) -> None:
        await self.async_update_values(
            **{
                CONF_LAST_SERVICE_DATE: self.today.isoformat(),
                CONF_LAST_SERVICE_KM: self.mileage or 0,
            }
        )

    async def async_inspection_done(self) -> None:
        months = calc.to_int(self.config.get(CONF_INSPECTION_INTERVAL)) or 12
        await self.async_update_values(
            **{CONF_INSPECTION_DATE: calc.add_months(self.today, months).isoformat()}
        )

    async def async_renew_insurance(self, key: str) -> None:
        """Przedłuż polisę o 12 mies. – od końca obecnej, a jeśli wygasła, od dziś."""
        current = calc.parse_date(self.config.get(key))
        base = current if current and current >= self.today else self.today
        await self.async_update_values(**{key: calc.add_months(base, 12).isoformat()})

    async def async_renew_oc(self) -> None:
        await self.async_renew_insurance(CONF_OC_DATE)

    async def async_renew_ac(self) -> None:
        await self.async_renew_insurance(CONF_AC_DATE)

    async def async_item_done(self, item: str) -> None:
        """Element wymieniony dziś przy obecnym przebiegu."""
        await self.async_update_values(
            **{
                item_key(item, "last_date"): self.today.isoformat(),
                item_key(item, "last_km"): self.mileage or 0,
            }
        )

    # --- elementy eksploatacyjne -------------------------------------------

    def item_due_date(self, item: str) -> date | None:
        return calc.item_due_date(self.config, item)

    def item_due_km(self, item: str) -> int | None:
        return calc.item_due_km(self.config, item)

    def item_km_left(self, item: str) -> int | None:
        return calc.item_km_left(self.config, item)

    def extra_date(self, kind: str) -> date | None:
        return calc.extra_date(self.config, kind)
