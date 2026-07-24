# Trophy Hunter Dashboard

A personal PlayStation trophy dashboard — rebuilt as a **FastAPI backend + React SPA**
(from the original Streamlit app by
[gonz4lex](https://github.com/gonz4lex/trophy-hunter-dashboard)).

Your **own** profile's data comes from the **official PlayStation Network API**
(via an NPSSO token): trophies, rarity, earned dates, and **real playtime** — no
Cloudflare in the way. Other public profiles fall back to best-effort PSNProfiles
scraping.

## Architecture

- **`backend/`** — FastAPI. PSN official API (PSNAWP) as the primary source for the
  token owner + a PSNProfiles scraper fallback, a 24-hour file cache, and REST + SSE
  endpoints.
- **`frontend/`** — Vite + React + TypeScript + Tailwind ("Trophy Gold" dark theme).
  Pages: Overview, Games, Timeline, Milestones, Data.

## Setup (first time)

1. **Backend** (Python 3.10+):
   ```powershell
   cd backend
   python -m venv .venv
   .venv\Scripts\python.exe -m pip install -r requirements.txt
   ```
2. **Frontend** (Node 18+):
   ```powershell
   cd frontend
   npm install
   ```
3. **PSN token** — copy `.env.example` to `.env` (in the repo root) and set `PSN_NPSSO`:
   - Log into playstation.com, then open
     `https://ca.account.sony.com/api/v1/ssocookie` and copy the `npsso` value.
   - `.env` is gitignored. The token expires roughly every two months — refresh it
     when your trophies stop loading.

## Run

- **Easiest — double-click `run.cmd`** in the project folder (File Explorer). It
  starts the backend (`:8000`) + frontend (`:5173`) in two windows and opens your
  dashboard in the browser. Close those two windows to stop the app.
- From a terminal instead: `run.cmd`, or `./run.ps1` (PowerShell).
- **Manual:**
  - Backend: `cd backend; .venv\Scripts\python.exe -m uvicorn app.main:app --port 8000`
  - Frontend: `cd frontend; npm run dev`
- Then open **http://localhost:5173** and enter your PSN ID.

## Notes

- The first load of a large library is slow (the PSN API is per-game and rate-limited);
  it's cached for 24 hours afterwards.
- PSNProfiles scraping is currently blocked by Cloudflare's managed challenge, so
  looking up *other* public profiles won't work until that's addressed — your own
  profile via the PSN API is unaffected.

## Tests

```powershell
cd backend; .venv\Scripts\python.exe -m pytest -q
```

## License

[MIT](LICENSE). Trophy data © Sony / PSNProfiles.
