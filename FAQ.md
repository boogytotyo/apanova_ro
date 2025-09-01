# FAQ — Integrare Apanova România

### ❓ Nu se autentifică, primesc eroare 401
- Verifică emailul și parola (trebuie să fie aceleași ca în aplicația web Apanova).
- API-ul poate bloca temporar contul după prea multe încercări → așteaptă câteva minute și reîncearcă.

### ❓ Nu apar atributele senzorilor
- Verifică logurile: *Settings → System → Logs → custom_components.apanova_ro*.
- Cele mai frecvente cauze: token expirat sau răspuns incomplet de la API.

### ❓ Pot instala prin HACS?
Da. Integrarea este compatibilă HACS ca **Custom Repository**.

### ❓ Pot partaja integrarea cu alt cont?
Da, atâta timp cât ai emailul și parola acelui cont. Fiecare instanță poate fi configurată separat.

### ❓ E integrat oficial în Home Assistant?
Nu. Este un **custom component** comunitar, nu parte din distribuția oficială Home Assistant.

### ❓ Cum raportez probleme?
- Deschide un [Issue](https://github.com/boogytotyo/apanova_ro/issues) cu loguri și pașii pentru a reproduce.
- Menționează versiunea Home Assistant și versiunea integrării.
