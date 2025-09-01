from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant

from .const import USER_AGENT

_LOGGER = logging.getLogger(__name__)


class ApanovaError(Exception):
    pass


def _explain_status(code: int) -> str:
    m = {
        200: "OK (200)",
        400: "Cerere invalidă (400)",
        401: "Autentificare eșuată (401)",
        403: "Acces refuzat (403)",
        404: "Resursă inexistentă (404)",
        429: "Prea multe cereri (429)",
        0: "Eroare rețea (0)",
    }
    return m.get(code, f"HTTP {code}")


def _content(o: Any) -> Any:
    if isinstance(o, dict) and "content" in o and o["content"] not in (None, {}):
        return o["content"]
    return o


class ApanovaClient:
    def __init__(self, hass: HomeAssistant, cfg: dict[str, Any]):
        self._hass = hass
        self._email = cfg.get("email")
        self._password = cfg.get("password")
        self._token: str | None = None
        self._user_id: str | None = None
        self._session: aiohttp.ClientSession | None = None
        self._login_payload: dict[str, Any] = {}
        self._cached_user_details: dict[str, Any] = {}

    async def _session_get(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "application/json",
                }
            )
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def _fetch(
        self, method: str, url: str, data: dict | None = None, use_auth: bool = True
    ) -> dict:
        s = await self._session_get()
        headers = {}
        if data is not None:
            headers["Content-Type"] = "application/json; charset=utf-8"
        if use_auth and self._token:
            headers["x-auth-token"] = self._token

        async with s.request(method, url, json=data, headers=headers) as resp:
            code = resp.status
            try:
                payload = await resp.json(content_type=None)
            except Exception:
                payload = {}
            if code >= 400:
                raise ApanovaError(
                    f"Eroare API {url} → {_explain_status(code)} // payload keys: {list(payload.keys())}"
                )
            return payload

    async def login(self) -> None:
        urls = [
            "https://security-client.apanovabucuresti.ro/api/Login",
            "https://security-bo.apanovabucuresti.ro/api/Login",
        ]
        payloads = [
            {"userMail": self._email, "password": self._password},
            {"email": self._email, "password": self._password},
            {"username": self._email, "password": self._password},
            {"BodyCredentials": {"Email": self._email, "Password": self._password}},
        ]
        last_error: Exception | None = None
        for u in urls:
            for p in payloads:
                try:
                    data = await self._fetch("POST", u, p, use_auth=False)
                    token = data.get("accessToken") or data.get("token") or data.get("access_token")
                    user_id = (
                        data.get("userId")
                        or data.get("UserId")
                        or (data.get("userData") or {}).get("UserId")
                    )
                    if token:
                        self._token = token
                        self._user_id = user_id
                        self._login_payload = data
                        return
                except Exception as e:
                    last_error = e
        raise ApanovaError(f"Nu s-a putut obține token. Ultima eroare: {last_error}")

    async def _ensure_login(self):
        if not self._token:
            await self.login()

    async def get_user_details(self) -> dict:
        await self._ensure_login()
        if not self._user_id:
            try:
                curr = await self._fetch(
                    "GET", "https://client-authorization.apanovabucuresti.ro/api/User"
                )
                uid = curr.get("userId") or (curr.get("userData") or {}).get("UserId")
                if uid:
                    self._user_id = uid
            except Exception:
                pass
        if not self._user_id:
            return {}
        details = await self._fetch(
            "GET", f"https://client-authorization.apanovabucuresti.ro/api/User/{self._user_id}"
        )
        self._cached_user_details = details or {}
        return details

    async def get_cod_client(self) -> str:
        payload = (
            (self._cached_user_details.get("userData") or {}).get("Payload")
            if self._cached_user_details
            else {}
        )
        if isinstance(payload, dict):
            cod = payload.get("clientNumber")
            if cod:
                return str(cod).lstrip("0")
        await self._ensure_login()
        url = f"https://client-authorization.apanovabucuresti.ro/api/ClientAuthorization/GetCodClientListByToken?token={self._token}"
        data = await self._fetch("GET", url)
        val = data
        if isinstance(val, list) and val:
            val = val[0]
        elif isinstance(val, dict):
            for k in ("codes", "list", "items", "data", "result", "value", "ClientNumber"):
                if k in val and val[k]:
                    val = val[k]
                    if isinstance(val, list) and val:
                        val = val[0]
                    break
        if isinstance(val, dict):
            cod = (
                val.get("cod")
                or val.get("code")
                or val.get("clientNumber")
                or val.get("ClientNumber")
                or val.get("id")
                or val.get("value")
            )
        else:
            cod = val
        if not cod:
            raise ApanovaError("Nu am putut determina codul client.")
        return str(cod).lstrip("0")

    async def get_consumption_points(self, cod: str) -> dict:
        await self._ensure_login()
        return await self._fetch(
            "GET",
            f"https://callistogateway.apanovabucuresti.ro/api/v2/apiclientconsumptionpoint/{cod}",
        )

    async def get_contract(self, cod: str) -> dict:
        await self._ensure_login()
        return await self._fetch(
            "GET", f"https://callistogateway.apanovabucuresti.ro/api/v2/apiclientcontract/{cod}"
        )

    async def get_payments(self, cod: str) -> dict:
        await self._ensure_login()
        return await self._fetch(
            "GET", f"https://callistogateway.apanovabucuresti.ro/api/v2/apiclientpayments/{cod}"
        )

    async def get_unpaid(self, cod: str) -> dict:
        await self._ensure_login()
        return await self._fetch(
            "GET",
            f"https://callistogateway.apanovabucuresti.ro/api/v2/apiclientunpaidinvoices?clientNumber={cod}",
        )

    async def get_invoices_year(self, cod: str, year: int) -> dict:
        await self._ensure_login()
        return await self._fetch(
            "GET",
            f"https://callistogateway.apanovabucuresti.ro/api/v2/apiclientinvoices?clientNumber={cod}&dateFrom={year}-01-01&dateTo={year}-12-31",
        )

    async def get_check_window(self, cod: str) -> dict:
        await self._ensure_login()
        return await self._fetch(
            "GET",
            f"https://callistogateway.apanovabucuresti.ro/api/v2/apiclientcheckmeterautoreading/{cod}",
        )

    async def get_index_history(self, cod: str, loc: str, contor: str, year: int) -> dict:
        await self._ensure_login()
        url = f"https://callistogateway.apanovabucuresti.ro/api/v2/apiclientindexhistory?clientNumber={cod}&consumptionPointCode={loc}&meterSnr={contor}&year={year}"
        return await self._fetch("GET", url)

    async def get_water_quality(self) -> dict:
        await self._ensure_login()
        url = "https://callistogateway.apanovabucuresti.ro/api/v2/apiwater/quality"
        return await self._fetch("GET", url)

    def _first(self, xs):
        if isinstance(xs, list) and xs:
            return xs[0]
        return xs

    def _extract_contor_loc(self, consumption: dict, check: dict):
        contor = None
        loc = None
        c = _content(consumption)
        if isinstance(c, dict):
            info = self._first(c.get("ConsumptionPointInfo") or [])
            if isinstance(info, dict):
                cm = info.get("ConsumptionMeters") or []
                if cm:
                    contor = str(self._first(cm))
                if not loc:
                    loc = str(info.get("ConsumptionPointCode") or "")
        ch = _content(check)
        if isinstance(ch, dict):
            details = self._first(ch.get("MeterReadingDetails") or [])
            if isinstance(details, dict):
                contor = contor or str(details.get("Sernr") or "")
                loc = loc or str(details.get("ConsumptionPointIdentifier") or "")
        return contor, loc

    async def refresh_all(self) -> dict:
        await self._ensure_login()
        user_details = await self.get_user_details()
        cod = await self.get_cod_client()
        consumption = await self.get_consumption_points(cod)
        contract = await self.get_contract(cod)
        payments = await self.get_payments(cod)
        unpaid = await self.get_unpaid(cod)
        invoices = await self.get_invoices_year(cod, datetime.now().year)
        check = await self.get_check_window(cod)
        water = await self.get_water_quality()

        contor, loc = self._extract_contor_loc(consumption, check)

        index_history = {}
        try:
            if contor and loc:
                index_history = await self.get_index_history(cod, loc, contor, datetime.now().year)
        except Exception as e:
            _LOGGER.debug("Index history load failed: %s", e)

        return {
            "cod": str(cod),
            "login_payload": self._login_payload,
            "user_details": user_details or {},
            "consumption": consumption or {},
            "contract": contract or {},
            "payments": payments or {},
            "unpaid": unpaid or {},
            "invoices": invoices or {},
            "check": check or {},
            "contor": contor,
            "loc": loc,
            "index_history": index_history or {},
            "water": water or {},
        }
