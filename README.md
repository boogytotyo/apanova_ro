# Apanova România — Integrare Home Assistant

[![Release](https://img.shields.io/github/v/release/boogytotyo/apanova_ro?display_name=tag&sort=semver)](https://github.com/boogytotyo/apanova_ro/releases)
[![🚀 Release](https://github.com/boogytotyo/apanova_ro/actions/workflows/release.yml/badge.svg)](https://github.com/boogytotyo/apanova_ro/actions/workflows/release.yml)
[![Downloads](https://img.shields.io/github/downloads/boogytotyo/apanova_ro/total.svg)](https://github.com/boogytotyo/apanova_ro/releases)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-blue.svg)](https://hacs.xyz/)
[![🧹 Lint](https://github.com/boogytotyo/apanova_ro/actions/workflows/lint.yml/badge.svg)](https://github.com/boogytotyo/apanova_ro/actions/workflows/lint.yml)
[![✅ Validate](https://github.com/boogytotyo/apanova_ro/actions/workflows/validate.yml/badge.svg)](https://github.com/boogytotyo/apanova_ro/actions/workflows/validate.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)


Integrare **custom** pentru Home Assistant care afișează datele contului tău **Apanova București**: facturi, restanțe, index curent, istoric index și calitatea apei.

> ⚠️ Acest proiect **nu este afiliat cu Apanova București** și nu are suport oficial din partea companiei.

---

## ✨ Funcționalități (entități)

- `sensor.apanova_date_utilizator` — cod client; atribute: email, nume, telefon, adresă, installation, cod loc consum, contor, contract.
- `sensor.apanova_arhiva_facturi` — ultima factură; atribute: facturile lunare + total și număr plăți.
- `sensor.apanova_factura_restanta` — ultima factură restantă (sau 0); atribute: facturile restante, total și count.
- `sensor.apanova_index_curent` — index curent; atribute: cod loc, ultima citire, contor, fereastră index, IsSmart.
- `sensor.apanova_istoric_index` — ultimul index maxim; atribute: perioade `DD Lll - DD Lll | INDEX | CONSUM`.
- `sensor.apanova_calitate_apa` — calitatea apei; atribute: tabel cu sectoare, clor, pH și turbiditate.
- `sensor.apanova_ro_update` — versiune instalată și disponibilă.

---

## 🔧 Instalare

### 1. Manual
1. Descarcă ultima versiune din [Releases](https://github.com/boogytotyo/apanova_ro/releases).
2. Copiază folderul `custom_components/apanova_ro` în:
   - Home Assistant OS/Supervised/Container: `/config/custom_components/apanova_ro/`
   - Home Assistant Core (venv): `~/.homeassistant/custom_components/apanova_ro/`
3. Repornește Home Assistant.
4. Adaugă integrarea din UI → *Settings → Devices & Services* → **Add Integration** → „Apanova România”.

### 2. HACS (Custom repo)
1. HACS → *Integrations* → **⋮** → **Custom repositories**.
2. URL: `https://github.com/boogytotyo/apanova_ro`, Category: `Integration`.
3. Instalează „Apanova România”.
4. Repornește HA, apoi adaugă integrarea din UI.

---

## 🔐 Autentificare

- Necesită **email** și **parolă** (aceleași ca în aplicația/aplicația web Apanova).
- Integrarea obține token (`x-auth-token`) și `userId`, apoi apelează endpointurile oficiale.
- Tokenul este stocat doar în memoria Home Assistant și nu părăsește sistemul tău.

---

## 🛠️ Dezvoltare

- Testare cu **pytest-homeassistant-custom-component**.
- Validare automată cu **hassfest** și **HACS action**.
- Stil de cod verificat cu **ruff** și **black**.
- Workflows GitHub Actions: `lint`, `validate`, `release`.

---

## 📝 Licență

[MIT](LICENSE)  
Vezi și [PRIVACY.md](PRIVACY.md) și [FAQ.md](FAQ.md).

