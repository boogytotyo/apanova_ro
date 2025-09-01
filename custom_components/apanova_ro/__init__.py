from __future__ import annotations
import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, UPDATE_INTERVAL_MINUTES
from .api import ApanovaClient

_LOGGER = logging.getLogger(__name__)

# ✅ declară schema pentru integrare „config-entry only”
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    # optional: nu mai face nimic pe YAML; doar semnalăm că domeniul există
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    client = ApanovaClient(hass, entry.data)
    coordinator = DataCoordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
    }
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok

class DataCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, client: ApanovaClient):
        super().__init__(
            hass,
            _LOGGER,
            name="apanova_ro",
            update_interval=timedelta(minutes=UPDATE_INTERVAL_MINUTES),
        )
        self.client = client

    async def _async_update_data(self):
        return await self.client.refresh_all()
