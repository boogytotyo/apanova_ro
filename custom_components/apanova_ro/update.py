from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import aiohttp
from homeassistant.components.update import UpdateEntity, UpdateEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.loader import async_get_integration

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

REPO = "boogytotyo/apanova_ro"
RELEASE_API = f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASE_URL = f"https://github.com/{REPO}/releases/latest"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up the update entity."""
    # aflăm versiunea instalată din manifest
    integration = await async_get_integration(hass, DOMAIN)
    installed_version: str = integration.version or "0.0.0"

    # coordinator care verifică ultima versiune publică
    session = async_get_clientsession(hass)

    async def _fetch_latest() -> dict[str, Any]:
        try:
            async with session.get(RELEASE_API, timeout=15) as resp:
                if resp.status != 200:
                    raise UpdateFailed(f"GitHub API status {resp.status}")
                data = await resp.json()
                tag = (data.get("tag_name") or "").lstrip("v").strip()
                name = data.get("name") or tag
                body = data.get("body") or ""
                html_url = data.get("html_url") or RELEASE_URL
                if not tag:
                    raise UpdateFailed("Nu am găsit tag_name în răspunsul GitHub.")
                return {
                    "latest": tag,
                    "name": name,
                    "release_notes": body,
                    "release_url": html_url,
                }
        except (TimeoutError, aiohttp.ClientError) as e:
            raise UpdateFailed(f"Eroare la interogarea GitHub: {e}") from e

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"{DOMAIN}_update_coordinator",
        update_method=_fetch_latest,
        update_interval=timedelta(hours=12),
    )

    # primele date (nu blocăm, lăsăm HA să încarce entitatea și să actualizeze apoi)
    await coordinator.async_config_entry_first_refresh()

    entity = ApanovaUpdateEntity(entry, installed_version, coordinator)
    async_add_entities([entity])


class ApanovaUpdateEntity(CoordinatorEntity[DataUpdateCoordinator], UpdateEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        entry: ConfigEntry,
        installed_version: str,
        coordinator: DataUpdateCoordinator,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._installed_version = installed_version
        self._attr_name = "Apanova România Update"
        self._attr_unique_id = f"{entry.entry_id}_update"
        self._attr_entity_category = "diagnostic"
        # Arătăm un link spre pagină chiar dacă API-ul pică
        self._fallback_release_url = RELEASE_URL

    @property
    def installed_version(self) -> str:
        return self._installed_version

    @property
    def latest_version(self) -> str | None:
        latest = (self.coordinator.data or {}).get("latest")
        return latest or self._installed_version  # dacă nu avem date, nu spamăm cu „unknown”

    @property
    def release_url(self) -> str | None:
        return (self.coordinator.data or {}).get("release_url") or self._fallback_release_url

    @property
    def release_notes(self) -> str | None:
        return (self.coordinator.data or {}).get("release_notes")

    @property
    def supported_features(self) -> int:
        # Nu facem install din UI; expunem doar release notes + link
        return UpdateEntityFeature.RELEASE_NOTES

    @property
    def available(self) -> bool:
        # Dacă GitHub e nedisponibil temporar, entitatea rămâne „available”,
        # doar că latest==installed.
        return True
