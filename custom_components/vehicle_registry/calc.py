"""Czysta logika liczenia terminów (bez zależności od stanu Home Assistant)."""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date
from typing import Any

from .const import (
    CONF_AC_DATE,
    CONF_INSPECTION_DATE,
    CONF_LAST_SERVICE_DATE,
    CONF_LAST_SERVICE_KM,
    CONF_MILEAGE,
    CONF_OC_DATE,
    CONF_SERVICE_INTERVAL_KM,
    CONF_SERVICE_INTERVAL_MONTHS,
    CONF_WARN_DAYS,
    CONF_WARN_KM,
    EXTRA_DATES,
    MAINTENANCE_ITEMS,
    KIND_AC,
    KIND_INSPECTION,
    KIND_OC,
    KIND_SERVICE,
    KIND_SERVICE_KM,
    item_key,
)


@dataclass(frozen=True)
class Deadline:
    """Pojedynczy termin z datą."""

    kind: str
    due: date
    days_left: int


def parse_date(value: Any) -> date | None:
    """Zamień wartość z konfiguracji na datę (lub None)."""
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def to_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def add_months(d: date, months: int) -> date:
    """Dodaj miesiące, przycinając dzień do końca miesiąca (31.01 + 1 = 28/29.02)."""
    m = d.month - 1 + months
    year = d.year + m // 12
    month = m % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def next_service_date(cfg: dict[str, Any]) -> date | None:
    last = parse_date(cfg.get(CONF_LAST_SERVICE_DATE))
    months = to_int(cfg.get(CONF_SERVICE_INTERVAL_MONTHS))
    if last is None or not months:
        return None
    return add_months(last, months)


def next_service_km(cfg: dict[str, Any]) -> int | None:
    last_km = to_int(cfg.get(CONF_LAST_SERVICE_KM))
    interval = to_int(cfg.get(CONF_SERVICE_INTERVAL_KM))
    if last_km is None or not interval:
        return None
    return last_km + interval


def km_to_service(cfg: dict[str, Any]) -> int | None:
    due_km = next_service_km(cfg)
    mileage = to_int(cfg.get(CONF_MILEAGE))
    if due_km is None or mileage is None:
        return None
    return due_km - mileage


# --- elementy eksploatacyjne ---------------------------------------------------


def item_enabled(cfg: dict[str, Any], item: str) -> bool:
    return (
        parse_date(cfg.get(item_key(item, "last_date"))) is not None
        or to_int(cfg.get(item_key(item, "last_km"))) is not None
    )


def item_due_date(cfg: dict[str, Any], item: str) -> date | None:
    last = parse_date(cfg.get(item_key(item, "last_date")))
    months = to_int(cfg.get(item_key(item, "interval_months")))
    if last is None or not months:
        return None
    return add_months(last, months)


def item_due_km(cfg: dict[str, Any], item: str) -> int | None:
    last_km = to_int(cfg.get(item_key(item, "last_km")))
    interval = to_int(cfg.get(item_key(item, "interval_km")))
    if last_km is None or not interval:
        return None
    return last_km + interval


def item_km_left(cfg: dict[str, Any], item: str) -> int | None:
    due_km = item_due_km(cfg, item)
    mileage = to_int(cfg.get(CONF_MILEAGE))
    if due_km is None or mileage is None:
        return None
    return due_km - mileage


def extra_date(cfg: dict[str, Any], kind: str) -> date | None:
    return parse_date(cfg.get(f"{kind}_date"))


# --- zbiorcze -------------------------------------------------------------------


def deadlines(cfg: dict[str, Any], today: date) -> list[Deadline]:
    """Wszystkie terminy datowe, posortowane od najbliższego."""
    items: list[tuple[str, date | None]] = [
        (KIND_INSPECTION, parse_date(cfg.get(CONF_INSPECTION_DATE))),
        (KIND_OC, parse_date(cfg.get(CONF_OC_DATE))),
        (KIND_AC, parse_date(cfg.get(CONF_AC_DATE))),
        (KIND_SERVICE, next_service_date(cfg)),
    ]
    items += [(item, item_due_date(cfg, item)) for item in MAINTENANCE_ITEMS]
    items += [(kind, extra_date(cfg, kind)) for kind in EXTRA_DATES]
    result = [
        Deadline(kind, due, (due - today).days) for kind, due in items if due is not None
    ]
    return sorted(result, key=lambda d: d.due)


def attention(cfg: dict[str, Any], today: date) -> list[dict[str, Any]]:
    """Terminy, które są blisko lub już minęły (wg progów ostrzeżeń)."""
    warn_days = to_int(cfg.get(CONF_WARN_DAYS)) or 0
    warn_km = to_int(cfg.get(CONF_WARN_KM)) or 0
    issues: list[dict[str, Any]] = [
        {"kind": d.kind, "due": d.due.isoformat(), "days_left": d.days_left}
        for d in deadlines(cfg, today)
        if d.days_left <= warn_days
    ]
    km_left = km_to_service(cfg)
    if km_left is not None and km_left <= warn_km:
        issues.append(
            {"kind": KIND_SERVICE_KM, "due_km": next_service_km(cfg), "km_left": km_left}
        )
    for item in MAINTENANCE_ITEMS:
        km_left = item_km_left(cfg, item)
        if km_left is not None and km_left <= warn_km:
            issues.append(
                {
                    "kind": f"{item}_km",
                    "due_km": item_due_km(cfg, item),
                    "km_left": km_left,
                }
            )
    return issues
