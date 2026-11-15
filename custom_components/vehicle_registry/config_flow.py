"""Formularze dodawania i edycji pojazdu."""

from __future__ import annotations

import re
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.data_entry_flow import section
from homeassistant.helpers.selector import (
    DateSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
)

from . import calc
from .const import (
    CONF_AC_DATE,
    CONF_FUEL,
    CONF_INSPECTION_DATE,
    CONF_INSPECTION_INTERVAL,
    CONF_LAST_SERVICE_DATE,
    CONF_LAST_SERVICE_KM,
    CONF_MAKE,
    CONF_MILEAGE,
    CONF_MODEL,
    CONF_NAME,
    CONF_NOTES,
    CONF_OC_DATE,
    CONF_OC_INSURER,
    CONF_OC_POLICY,
    CONF_PLATE,
    CONF_SERVICE_INTERVAL_KM,
    CONF_SERVICE_INTERVAL_MONTHS,
    CONF_VIN,
    CONF_WARN_DAYS,
    CONF_WARN_KM,
    CONF_YEAR,
    DEFAULTS,
    DOMAIN,
    EXTRA_DATES,
    FUEL_TYPES,
    INT_KEYS,
    ITEM_FIELDS,
    ITEM_INT_FIELDS,
    MAINTENANCE_ITEMS,
    item_key,
)


def _num(minimum: int, maximum: int, unit: str | None = None) -> NumberSelector:
    config = NumberSelectorConfig(
        min=minimum, max=maximum, step=1, mode=NumberSelectorMode.BOX
    )
    if unit:
        # HA nie akceptuje unit_of_measurement=None – pole musi być pominięte
        config["unit_of_measurement"] = unit
    return NumberSelector(config)


IDENTITY_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): TextSelector(),
        vol.Required(CONF_PLATE): TextSelector(),
        vol.Optional(CONF_MAKE): TextSelector(),
        vol.Optional(CONF_MODEL): TextSelector(),
        vol.Optional(CONF_YEAR): _num(1900, 2100),
        vol.Optional(CONF_VIN): TextSelector(),
        vol.Optional(CONF_FUEL): SelectSelector(
            SelectSelectorConfig(
                options=FUEL_TYPES,
                translation_key="fuel",
                mode=SelectSelectorMode.DROPDOWN,
            )
        ),
        vol.Required(CONF_MILEAGE): _num(0, 2_000_000, "km"),
        vol.Optional(CONF_NOTES): TextSelector(TextSelectorConfig(multiline=True)),
    }
)

DATES_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_INSPECTION_DATE): DateSelector(),
        vol.Required(CONF_INSPECTION_INTERVAL): _num(1, 60, "mies."),
        vol.Optional(CONF_OC_DATE): DateSelector(),
        vol.Optional(CONF_OC_INSURER): TextSelector(),
        vol.Optional(CONF_OC_POLICY): TextSelector(),
        vol.Optional(CONF_AC_DATE): DateSelector(),
        vol.Optional(CONF_LAST_SERVICE_DATE): DateSelector(),
        vol.Optional(CONF_LAST_SERVICE_KM): _num(0, 2_000_000, "km"),
        vol.Required(CONF_SERVICE_INTERVAL_MONTHS): _num(1, 60, "mies."),
        vol.Required(CONF_SERVICE_INTERVAL_KM): _num(500, 100_000, "km"),
        vol.Required(CONF_WARN_DAYS): _num(0, 365, "dni"),
        vol.Required(CONF_WARN_KM): _num(0, 20_000, "km"),
    }
)

EXTRAS_SCHEMA = vol.Schema(
    {vol.Optional(f"{kind}_date"): DateSelector() for kind in EXTRA_DATES}
)


def _maintenance_schema(current: dict[str, Any]) -> vol.Schema:
    """Jedna zwijana sekcja na element; aktywne elementy są rozwinięte."""

    def opt(item: str, field: str) -> vol.Optional:
        value = current.get(item_key(item, field))
        if value is None:
            return vol.Optional(field)
        return vol.Optional(field, description={"suggested_value": value})

    fields: dict[Any, Any] = {}
    for item in MAINTENANCE_ITEMS:
        inner = vol.Schema(
            {
                opt(item, "last_date"): DateSelector(),
                opt(item, "last_km"): _num(0, 2_000_000, "km"),
                opt(item, "interval_months"): _num(1, 240, "mies."),
                opt(item, "interval_km"): _num(500, 1_000_000, "km"),
            }
        )
        fields[vol.Required(item)] = section(
            inner, {"collapsed": not calc.item_enabled(current, item)}
        )
    return vol.Schema(fields)


def _clean_value(value: Any, as_int: bool) -> Any:
    if isinstance(value, str):
        value = value.strip() or None
    if as_int and value is not None:
        value = int(value)
    return value


def _clean(schema: vol.Schema, user_input: dict[str, Any]) -> dict[str, Any]:
    """Weź wszystkie pola schematu – brakujące (wyczyszczone) zapisz jako None."""
    result: dict[str, Any] = {}
    for marker in schema.schema:
        key = marker.schema
        result[key] = _clean_value(user_input.get(key), key in INT_KEYS)
    if result.get(CONF_PLATE):
        result[CONF_PLATE] = re.sub(r"\s+", " ", result[CONF_PLATE]).upper()
    if result.get(CONF_VIN):
        result[CONF_VIN] = result[CONF_VIN].replace(" ", "").upper()
    return result


def _clean_maintenance(user_input: dict[str, Any]) -> dict[str, Any]:
    """Spłaszcz sekcje do kluczy <element>_<pole>."""
    result: dict[str, Any] = {}
    for item in MAINTENANCE_ITEMS:
        values = user_input.get(item) or {}
        for field in ITEM_FIELDS:
            result[item_key(item, field)] = _clean_value(
                values.get(field), field in ITEM_INT_FIELDS
            )
    return result


def _validate_identity(data: dict[str, Any]) -> dict[str, str]:
    errors: dict[str, str] = {}
    if not data.get(CONF_NAME):
        errors[CONF_NAME] = "required"
    if not data.get(CONF_PLATE):
        errors[CONF_PLATE] = "required"
    vin = data.get(CONF_VIN)
    if vin and not re.fullmatch(r"[A-HJ-NPR-Z0-9]{17}", vin):
        errors[CONF_VIN] = "invalid_vin"
    return errors


def _plate_id(plate: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", plate.upper())


def _title(data: dict[str, Any]) -> str:
    return f"{data[CONF_NAME]} ({data[CONF_PLATE]})"


class VehicleRegistryConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            data = _clean(IDENTITY_SCHEMA, user_input)
            errors = _validate_identity(data)
            if not errors:
                await self.async_set_unique_id(_plate_id(data[CONF_PLATE]))
                self._abort_if_unique_id_configured()
                self._data.update(data)
                return await self.async_step_dates()

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                IDENTITY_SCHEMA, user_input or {CONF_MILEAGE: 0}
            ),
            errors=errors,
        )

    async def async_step_dates(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            self._data.update(_clean(DATES_SCHEMA, user_input))
            return self.async_create_entry(
                title=_title(self._data), data={}, options=self._data
            )

        suggested = {**DEFAULTS, CONF_LAST_SERVICE_KM: self._data.get(CONF_MILEAGE)}
        return self.async_show_form(
            step_id="dates",
            data_schema=self.add_suggested_values_to_schema(DATES_SCHEMA, suggested),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return VehicleOptionsFlow()


class VehicleOptionsFlow(OptionsFlow):
    """Edycja pojazdu (Ustawienia → Urządzenia i usługi → Konfiguruj)."""

    @property
    def _current(self) -> dict[str, Any]:
        return {**DEFAULTS, **self.config_entry.data, **self.config_entry.options}

    def _save(self, changes: dict[str, Any]) -> ConfigFlowResult:
        return self.async_create_entry(data={**self._current, **changes})

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return self.async_show_menu(
            step_id="init",
            menu_options=["vehicle", "dates", "maintenance", "extras"],
        )

    async def async_step_vehicle(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            data = _clean(IDENTITY_SCHEMA, user_input)
            errors = _validate_identity(data)
            if not errors:
                new_id = _plate_id(data[CONF_PLATE])
                clash = any(
                    e.unique_id == new_id and e.entry_id != self.config_entry.entry_id
                    for e in self.hass.config_entries.async_entries(DOMAIN)
                )
                if clash:
                    errors[CONF_PLATE] = "already_configured"
                else:
                    self.hass.config_entries.async_update_entry(
                        self.config_entry, title=_title(data), unique_id=new_id
                    )
                    return self._save(data)

        return self.async_show_form(
            step_id="vehicle",
            data_schema=self.add_suggested_values_to_schema(
                IDENTITY_SCHEMA, user_input or self._current
            ),
            errors=errors,
        )

    async def async_step_dates(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self._save(_clean(DATES_SCHEMA, user_input))
        return self.async_show_form(
            step_id="dates",
            data_schema=self.add_suggested_values_to_schema(DATES_SCHEMA, self._current),
        )

    async def async_step_maintenance(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self._save(_clean_maintenance(user_input))
        return self.async_show_form(
            step_id="maintenance", data_schema=_maintenance_schema(self._current)
        )

    async def async_step_extras(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self._save(_clean(EXTRAS_SCHEMA, user_input))
        return self.async_show_form(
            step_id="extras",
            data_schema=self.add_suggested_values_to_schema(EXTRAS_SCHEMA, self._current),
        )