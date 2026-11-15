"""Kartoteka pojazdów – terminy badań, przeglądów i ubezpieczeń w Home Assistant."""

from __future__ import annotations

from datetime import datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_change

from .const import PLATFORMS
from .vehicle import Vehicle

type VehicleConfigEntry = ConfigEntry[Vehicle]


async def async_setup_entry(hass: HomeAssistant, entry: VehicleConfigEntry) -> bool:
    vehicle = Vehicle(hass, entry)
    entry.runtime_data = vehicle

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    @callback
    def _new_day(_now: datetime) -> None:
        # "dni do terminu" zmieniają się o północy
        vehicle.async_notify()

    entry.async_on_unload(
        async_track_time_change(hass, _new_day, hour=0, minute=0, second=5)
    )
    return True


async def _async_update_listener(hass: HomeAssistant, entry: VehicleConfigEntry) -> None:
    vehicle = entry.runtime_data
    if vehicle.internal_update:
        # zmiana z przycisku / przebiegu – encje już odświeżone
        vehicle.internal_update = False
        return
    # zmiana z formularza opcji – przeładuj (nazwa urządzenia, AC itp.)
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: VehicleConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
