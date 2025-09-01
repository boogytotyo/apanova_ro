from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import _content
from .const import DOMAIN, VERSION

_LOGGER = logging.getLogger(__name__)

RO_MONTHS = {
    1: "ianuarie",
    2: "februarie",
    3: "martie",
    4: "aprilie",
    5: "mai",
    6: "iunie",
    7: "iulie",
    8: "august",
    9: "septembrie",
    10: "octombrie",
    11: "noiembrie",
    12: "decembrie",
}


def money_num(v) -> float:
    try:
        return float(str(v).replace(",", "."))
    except Exception:
        return 0.0


def money(v) -> str:
    try:
        x = float(str(v).replace(",", "."))
        s = f"{x:,.2f}"
        s = s.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{s} lei"
    except Exception:
        return f"{v}"


def money_state(v) -> str:
    try:
        x = float(str(v).replace(",", "."))
        s = f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return s
    except Exception:
        return "0,00"


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    async_add_entities(
        [
            ApanovaDateUtilizatorSensor(coordinator, entry),
            ApanovaArhivaFacturiSensor(coordinator, entry),
            ApanovaFacturaRestantaSensor(coordinator, entry),
            ApanovaIndexCurentSensor(coordinator, entry),
            ApanovaIstoricIndexSensor(coordinator, entry),
            ApanovaCalitateApaSensor(coordinator, entry),
            ApanovaUpdateSensor(coordinator, entry),
        ],
        True,
    )


class BaseApanovaSensor(SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry):
        self.coordinator = coordinator
        self._entry = entry

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    async def async_update(self):
        await self.coordinator.async_request_refresh()

    @property
    def should_poll(self) -> bool:
        return False

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )


class ApanovaDateUtilizatorSensor(BaseApanovaSensor):
    _attr_icon = "mdi:account"
    _attr_name = "Apanova – Date utilizator/contract"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self.entity_id = "sensor.apanova_date_utilizator"

    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_date_utilizator"

    @property
    def native_value(self):
        return (self.coordinator.data.get("cod") or "").lstrip("0")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        d = self.coordinator.data
        u = d.get("user_details") or {}
        payload = (u.get("userData") or {}).get("Payload") or {}
        consumption = _content(d.get("consumption") or {})
        contract = _content(d.get("contract") or {})
        info = None
        if isinstance(consumption, dict):
            info_list = consumption.get("ConsumptionPointInfo") or []
            if isinstance(info_list, list) and info_list:
                info = info_list[0]
        addr = (info or {}).get("ConsumptionClientAddress")
        installation = (info or {}).get("ConsumptionInstallation") or contract.get(
            "Installation"
        )
        cpcode = (info or {}).get("ConsumptionPointCode")
        meters = (info or {}).get("ConsumptionMeters") or []
        contor = meters[0] if meters else None

        email = payload.get("email") or (u.get("userData") or {}).get("EMail")
        ln = payload.get("lastname") or payload.get("lastName") or ""
        fn = payload.get("firstname") or payload.get("firstName") or ""
        name = f"{ln} {fn}".strip() or None
        phone = payload.get("mobile")
        client_number = payload.get("clientNumber") or d.get("cod")
        contract_nr = (
            payload.get("contractNumber")
            or contract.get("ContractNumberWithAnb")
            or contract.get("ContractNumber")
        )

        return {
            "email": email,
            "nume": name,
            "telefon": phone,
            "adresa": addr,
            "cod client": client_number,
            "installation_number": installation,
            "cod_loc_consum": cpcode,
            "contor": contor,
            "contract": contract_nr,
            "icon": "mdi:account",
            "friendly_name": "Apanova – Date utilizator/contract",
        }


class ApanovaArhivaFacturiSensor(BaseApanovaSensor):
    _attr_icon = "mdi:cash-register"
    _attr_name = "Apanova – Arhivă facturi"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self.entity_id = "sensor.apanova_arhiva_facturi"

    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_arhiva_facturi"

    @property
    def native_value(self):
        inv = _content(self.coordinator.data.get("invoices") or {})
        invoices = inv.get("Invoices") or []
        latest = None
        latest_dt = None
        for it in invoices:
            d = it.get("DateIn") or it.get("InvoiceDate") or it.get("date")
            amt = it.get("Total") or it.get("value") or it.get("amount")
            if d and amt is not None:
                try:
                    dt = datetime.fromisoformat(str(d)[:10])
                except Exception:
                    continue
                if latest_dt is None or dt > latest_dt:
                    latest_dt = dt
                    latest = amt
        return money_state(latest) if latest is not None else "0,00"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        inv = _content(self.coordinator.data.get("invoices") or {})
        invoices = inv.get("Invoices") or []
        months: dict[str, Any] = {}
        for it in invoices:
            d = it.get("DateIn") or it.get("InvoiceDate") or it.get("date")
            amt = it.get("Total") or it.get("value") or it.get("amount")
            if d and amt is not None:
                try:
                    dt = datetime.fromisoformat(str(d)[:10])
                    key = RO_MONTHS.get(dt.month, dt.strftime("%B").lower())
                    months[key] = money(amt)
                except Exception:
                    continue
        count = len(
            [
                k
                for k in months.keys()
                if k
                not in (
                    "──────────",
                    "Plăți efectuate",
                    "Total suma achitată",
                    "icon",
                    "friendly_name",
                )
            ]
        )
        total = 0.0
        for v in months.values():
            num = v.replace(" lei", "").replace(".", "").replace(",", ".")
            try:
                total += float(num)
            except Exception:
                pass
        months["──────────"] = ""
        months["Plăți efectuate"] = count
        months["Total suma achitată"] = money(total)
        months["icon"] = "mdi:cash-register"
        months["friendly_name"] = "Apanova – Arhivă facturi"
        return months


class ApanovaFacturaRestantaSensor(BaseApanovaSensor):
    _attr_icon = "mdi:file-document-alert"
    _attr_name = "Apanova – Valoare factură restantă"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self.entity_id = "sensor.apanova_factura_restanta"

    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_factura_restanta"

    @property
    def native_value(self):
        unpaid = _content(self.coordinator.data.get("unpaid") or {})
        items = unpaid.get("Invoices") or []
        latest_val = None
        latest_dt = None
        for it in items:
            d = it.get("DateIn") or it.get("InvoiceDate") or it.get("date")
            v = (
                it.get("Sold")
                or it.get("Total")
                or it.get("value")
                or it.get("amount")
            )
            if v is None:
                continue
            dt = None
            if d:
                try:
                    dt = datetime.fromisoformat(str(d)[:10])
                except Exception:
                    dt = None
            if latest_dt is None or (dt and dt > latest_dt):
                latest_dt = dt
                latest_val = v
        return money_state(latest_val) if latest_val is not None else "0,00"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        unpaid = _content(self.coordinator.data.get("unpaid") or {})
        items = unpaid.get("Invoices") or []
        attrs: dict[str, Any] = {}
        if not items:
            attrs["Fara restante"] = ""
            attrs["──────────"] = ""
            attrs["Plăți restante"] = 0
            attrs["Total suma neachitată"] = money(0)
            attrs["icon"] = "mdi:file-document-alert"
            attrs["friendly_name"] = "Apanova – Valoare factură restantă"
            return attrs
        total = 0.0
        cnt = 0
        amounts: list[str] = []

        def get_dt(it):
            d = it.get("DateIn") or it.get("InvoiceDate") or it.get("date")
            try:
                return datetime.fromisoformat(str(d)[:10])
            except Exception:
                return datetime.min

        for it in sorted(items, key=get_dt):
            v = (
                it.get("Sold")
                or it.get("Total")
                or it.get("value")
                or it.get("amount")
            )
            if v is None:
                continue
            cnt += 1
            total += money_num(v)
            amounts.append(money(v).replace(" lei", ""))
        for a in amounts:
            attrs[a] = ""
        attrs["──────────"] = ""
        attrs["Plăți restante"] = cnt
        attrs["Total suma neachitată"] = money(total)
        attrs["icon"] = "mdi:file-document-alert"
        attrs["friendly_name"] = "Apanova – Valoare factură restantă"
        return attrs


class ApanovaIndexCurentSensor(BaseApanovaSensor):
    _attr_icon = "mdi:counter"
    _attr_name = "Apanova – Index curent"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self.entity_id = "sensor.apanova_index_curent"

    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_index_curent"

    @property
    def native_value(self):
        chk = _content(self.coordinator.data.get("check") or {})
        details = None
        if isinstance(chk, dict):
            details_list = chk.get("MeterReadingDetails") or []
            if isinstance(details_list, list) and details_list:
                details = details_list[0]
        if isinstance(details, dict):
            v = details.get("LastIndex")
            try:
                return int(v)
            except Exception:
                try:
                    return float(v) if v is not None else None
                except Exception:
                    return v
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        chk = _content(self.coordinator.data.get("check") or {})
        details = None
        if isinstance(chk, dict):
            details_list = chk.get("MeterReadingDetails") or []
            if isinstance(details_list, list) and details_list:
                details = details_list[0]

        def pick(o, *ks):
            for k in ks:
                if isinstance(o, dict) and k in o and o[k] is not None:
                    return o[k]
            return None

        return {
            "cod_loc_consum": pick(details or {}, "ConsumptionPointIdentifier"),
            "ultima_citire": pick(details or {}, "LastIndexDate"),
            "contor": pick(details or {}, "Sernr"),
            "fereastra_index": pick(details or {}, "Inperioada"),
            "IsSmart": pick(details or {}, "IsSmart"),
            "icon": "mdi:counter",
            "friendly_name": "Apanova – Index curent",
        }


class ApanovaIstoricIndexSensor(BaseApanovaSensor):
    _attr_icon = "mdi:counter"
    _attr_name = "Apanova – Istoric index"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self.entity_id = "sensor.apanova_istoric_index"

    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_istoric_index"

    @property
    def native_value(self):
        attrs = self.extra_state_attributes
        nums = []
        for k in attrs.keys():
            if " | " in k:
                parts = [p.strip() for p in k.split("|")]
                if len(parts) >= 2:
                    try:
                        nums.append(int(parts[1]))
                    except Exception:
                        try:
                            nums.append(float(parts[1].replace(",", ".")))
                        except Exception:
                            pass
        return max(nums) if nums else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        d = self.coordinator.data
        hist = _content(d.get("index_history") or {})
        attrs: dict[str, Any] = {}
        try:
            points = hist.get("ConsumptionPoints") or []
            if points:
                by_meter = points[0].get("IndexHistoryByMeter") or []
                if by_meter:
                    entries = by_meter[0].get("MeterIndexList") or []
                    parsed = []
                    for it in entries:
                        sd = it.get("StartDate") or it.get("Start")
                        ed = it.get("EndDate") or it.get("Date")
                        idx = it.get("Index")
                        cons = it.get("Consumption") or it.get("Cons")
                        if not (ed and idx):
                            continue
                        try:
                            sdt = (
                                datetime.fromisoformat(str(sd)[:10]) if sd else None
                            )
                            edt = datetime.fromisoformat(str(ed)[:10])
                            parsed.append((sdt, edt, idx, cons))
                        except Exception:
                            continue
                    parsed.sort(key=lambda x: x[1])  # EndDate asc

                    def label(dt):
                        if not dt:
                            return ""
                        return (
                            dt.strftime("%d %b")
                            .replace("May", "Mai")
                            .replace("Jul", "Iul")
                            .replace("Jun", "Iun")
                            .replace("Aug", "Aug")
                            .replace("Sep", "Sep")
                            .replace("Oct", "Oct")
                            .replace("Nov", "Noi")
                            .replace("Dec", "Dec")
                            .replace("Jan", "Ian")
                            .replace("Feb", "Feb")
                            .replace("Mar", "Mar")
                            .replace("Apr", "Apr")
                        )

                    for (sdt, edt, idx, cons) in reversed(parsed):
                        idxv = idx
                        try:
                            idxv = int(idx)
                        except Exception:
                            try:
                                idxv = float(str(idx).replace(",", "."))
                            except Exception:
                                idxv = idx
                        consv = ""
                        if cons is not None:
                            try:
                                consv = str(int(cons))
                            except Exception:
                                try:
                                    consv = str(float(str(cons).replace(",", ".")))
                                except Exception:
                                    consv = str(cons)
                        attrs[f"{label(sdt)} - {label(edt)} | {idxv} | {consv}"] = ""
        except Exception:
            pass
        attrs["friendly_name"] = "Apanova – Istoric index"
        attrs["icon"] = "mdi:counter"
        return attrs


class ApanovaCalitateApaSensor(BaseApanovaSensor):
    _attr_icon = "mdi:counter"
    _attr_name = "Apanova – Calitate apa"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self.entity_id = "sensor.apanova_calitate_apa"

    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_calitate_apa"

    @property
    def native_value(self):
        water = _content(self.coordinator.data.get("water") or {})
        return water.get("LastUpdateDate")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        water = _content(self.coordinator.data.get("water") or {})
        details = water.get("WaterDetails") or []
        attrs: dict[str, Any] = {}
        attrs["Sector \t | Clor |  PH  | Turbiditate"] = ""
        for it in details:
            sector = it.get("Sector")
            clor = it.get("Clor")
            ph = it.get("PH")
            turb = it.get("Turbiditate")
            attrs[f"{sector} | {clor} | {ph} | {turb}"] = ""
        if water.get("LastUpdateDate"):
            attrs[f"Last update: {water.get('LastUpdateDate')}"] = ""
        attrs["friendly_name"] = "Apanova – Calitate apa"
        attrs["icon"] = "mdi:counter"
        return attrs


class ApanovaUpdateSensor(BaseApanovaSensor):
    _attr_name = "Apanova România update"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self.entity_id = "sensor.apanova_ro_update"

    @property
    def unique_id(self) -> str:
        return f"{self._entry.entry_id}_update"

    @property
    def native_value(self):
        return f"v{VERSION}"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "auto_update": False,
            "display_precision": 0,
            "installed_version": f"v{VERSION}",
            "in_progress": False,
            "latest_version": f"v{VERSION}",
            "release_summary": None,
            "release_url": f"https://github.com/boogytotyo/apanova_ro/releases/v{VERSION}",
            "skipped_version": None,
            "title": None,
            "update_percentage": None,
            "entity_picture": "https://brands.home-assistant.io/_/apanova_ro/icon.png",
            "friendly_name": "Apanova România update",
            "supported_features": 23,
        }
