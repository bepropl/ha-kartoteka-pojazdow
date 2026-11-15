"""Stałe integracji Kartoteka pojazdów."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "vehicle_registry"

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.NUMBER,
    Platform.BUTTON,
    Platform.BINARY_SENSOR,
    Platform.CALENDAR,
]

# Dane identyfikacyjne
CONF_NAME = "name"
CONF_PLATE = "plate"
CONF_MAKE = "make"
CONF_MODEL = "model"
CONF_YEAR = "year"
CONF_VIN = "vin"
CONF_FUEL = "fuel"
CONF_MILEAGE = "mileage"
CONF_NOTES = "notes"

# Terminy
CONF_INSPECTION_DATE = "inspection_date"
CONF_INSPECTION_INTERVAL = "inspection_interval_months"
CONF_OC_DATE = "oc_date"
CONF_OC_INSURER = "oc_insurer"
CONF_OC_POLICY = "oc_policy"
CONF_AC_DATE = "ac_date"
CONF_LAST_SERVICE_DATE = "last_service_date"
CONF_LAST_SERVICE_KM = "last_service_km"
CONF_SERVICE_INTERVAL_MONTHS = "service_interval_months"
CONF_SERVICE_INTERVAL_KM = "service_interval_km"
CONF_WARN_DAYS = "warn_days"
CONF_WARN_KM = "warn_km"

FUEL_TYPES = ["petrol", "diesel", "lpg", "hybrid", "phev", "electric", "other"]

INT_KEYS = {
    CONF_YEAR,
    CONF_MILEAGE,
    CONF_INSPECTION_INTERVAL,
    CONF_LAST_SERVICE_KM,
    CONF_SERVICE_INTERVAL_MONTHS,
    CONF_SERVICE_INTERVAL_KM,
    CONF_WARN_DAYS,
    CONF_WARN_KM,
}

# Elementy eksploatacyjne z własnym interwałem: (domyślnie miesięcy, domyślnie km).
# Element jest aktywny, gdy podano datę lub przebieg ostatniej wymiany.
# Klucze w konfiguracji: <element>_last_date, _last_km, _interval_months, _interval_km
MAINTENANCE_ITEMS: dict[str, tuple[int | None, int | None]] = {
    "timing": (60, 120_000),  # rozrząd
    "brake_fluid": (24, None),  # płyn hamulcowy
    "cabin_filter": (12, 15_000),  # filtr kabinowy
    "battery": (60, None),  # akumulator
}
ITEM_FIELDS = ("last_date", "last_km", "interval_months", "interval_km")
ITEM_INT_FIELDS = ("last_km", "interval_months", "interval_km")


def item_key(item: str, field: str) -> str:
    return f"{item}_{field}"


# Pozostałe terminy z samą datą końca. Klucz w konfiguracji: <rodzaj>_date
EXTRA_DATES: tuple[str, ...] = (
    "warranty",  # gwarancja
    "assistance",
    "leasing",  # koniec leasingu / ostatnia rata
    "vignette_cz",
    "vignette_at",
    "vignette_sk",
)

DEFAULTS = {
    CONF_MILEAGE: 0,
    CONF_INSPECTION_INTERVAL: 12,
    CONF_SERVICE_INTERVAL_MONTHS: 12,
    CONF_SERVICE_INTERVAL_KM: 15000,
    CONF_WARN_DAYS: 30,
    CONF_WARN_KM: 1000,
}
for _item, (_months, _km) in MAINTENANCE_ITEMS.items():
    DEFAULTS[item_key(_item, "interval_months")] = _months
    DEFAULTS[item_key(_item, "interval_km")] = _km

# Rodzaje terminów
KIND_INSPECTION = "inspection"
KIND_OC = "oc"
KIND_AC = "ac"
KIND_SERVICE = "service"
KIND_SERVICE_KM = "service_km"
