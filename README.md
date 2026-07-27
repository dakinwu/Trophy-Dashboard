# Trophy Hunter Dashboard

A personal PlayStation trophy dashboard — rebuilt as a **FastAPI backend + React SPA**
(from the original Streamlit app by
[gonz4lex](https://github.com/gonz4lex/trophy-hunter-dashboard)).

Your **own** profile's data comes from the **official PlayStation Network API**
(via an NPSSO token): trophies, rarity, earned dates, and **real playtime** — no
Cloudflare in the way. Other public profiles fall back to PSNProfiles through a
visible nodriver-controlled Chrome session.

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
   .venv\Scripts\python.exe -m pip install -r requirements.lock
   ```
   `requirements.lock` contains the reproducible resolved environment;
   `requirements.txt` remains the short list of direct dependencies.
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
- Looking up another public profile opens a Chrome window while nodriver passes
  PSNProfiles' Cloudflare challenge. The first page can take a few minutes; the
  same browser session and cookies are reused for every trophy-log page.
- PSNProfiles guide difficulty and platinum-time data is loaded on demand from a
  game card. A cache miss opens the same visible Chrome flow; successful guide
  results and their exact URLs are cached for 90 days.
- Trophy rarity is source-labelled (`PSN` for the official API, `PSNP` for the
  value displayed by PSNProfiles) so the two player populations are not mixed.
- The Overview page can load PSNProfiles world and country rank on demand. These
  ranks cover public profiles tracked by PSNProfiles, not every PlayStation user,
  and successful lookups are cached for 6 hours.
- PSNine links resolve the site's own Simplified Chinese game name on first click,
  cache it, then open `https://www.psnine.com/psngame?title=<簡中名稱>`.

## Tests

```powershell
cd backend; .venv\Scripts\python.exe -m pytest -q
```

## License

[MIT](LICENSE). Trophy data © Sony / PSNProfiles.
