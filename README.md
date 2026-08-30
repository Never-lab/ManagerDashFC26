# ManagerDash FC 26

Dashboard **Node** per la career manager di EA Sports FC 26: rosa, mercato e crescita dal save locale. **Read-only** — non scrive sul file career.

## Requisiti

- Node.js 18+
- Python 3.10+
- Pacchetto Python `fc26-mcp` (parser T3DB del save)
- Un save career su Windows: `%LOCALAPPDATA%\EA SPORTS FC 26\settings\CmMgrC*`

## Install

```bash
npm install
pip install -r requirements.txt
```

Al primo avvio lo scout scarica un catalogo nomi/valori (SoFIFA dump pubblico) in `scout/data/` (gitignored).

## Avvio

```bash
npm start
```

Apri [http://localhost:3847](http://localhost:3847).

Opzionale:

```bash
set PORT=4000
set PYTHON=python
npm start
```

## Cosa fa

| Tab | Contenuto |
|-----|-----------|
| **Rosa** | Giocatori della tua squadra, valore stimato, Δ vs snapshot precedente |
| **Mercato** | Filtri OVR/POT/lega/ruolo, paginazione, solo nomi risolti |
| **Crescita** | Delta OVR/POT/valore dagli snapshot SQLite |

Formazioni supportate: `4-3-3`, `4-4-2`, `4-2-3-1` (fit per ruolo ricalcolati lato client sui dati già esportati).

## Architettura

- **Node / Express** — UI statica + API JSON (`/api/squad`, `/api/market`, `/api/growth`, `/api/refresh`)
- **Python** — `python -m scout.export` legge il save e stampa JSON su stdout

Niente HTML monolitico da 11MB: la pagina è leggera, i dati arrivano a pezzi.

## Note

- Il valore di mercato è **stimato** (il save FC 26 non lo memorizza).
- Gli snapshot restano in `scout/data/scout.db` (locale).
- Repo dedicato alla dashboard: non include Live Editor / DLL / mods.
