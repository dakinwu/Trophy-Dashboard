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
- **`frontend/`** — Vite + React + TypeScript + Tailwind CSS v4 + HeroUI v3
  ("Trophy Gold" dark theme), with Recharts for data visualization. Pages:
  Overview, Games, Trophy Advisor, Timeline, Milestones, Data.

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
4. **Gemini title resolver (recommended for Trophy Advisor)** — add your Google
   AI Studio key to the same repo-root `.env` file:

   ```dotenv
   GEMINI_API_KEY=your-key-here
   GEMINI_GROUNDING_MODEL=gemini-2.5-flash
   ```

   The key remains backend-only. Advisor uses Gemini 2.5 Flash with Google Search
   grounding to resolve localized library titles to verified English PSNProfiles
   search terms and caches each result for 180 days.
   Existing English titles are cleaned locally without spending Gemini quota;
   up to 12 unresolved localized titles share one grounded Gemini request so a
   failed lookup cannot discard the rest of a large batch. Unknown
   multi-game collections use the same key with Google Search grounding on
   Gemini 2.5 Flash; one analysis batch shares one call, and results are cached
   for 180 days. Known collections are resolved locally without a Gemini call.
   Restart `run.cmd` after adding or changing the key.

## Run

- **Easiest — double-click `run.cmd`** in the project folder (File Explorer). It
  starts the backend (`:8000`) + frontend (`:5173`) in two windows and opens your
  dashboard in the browser. Close those two windows to stop the app.
- From a terminal instead: `run.cmd`, or `./run.ps1` (PowerShell).
- **Manual:**
  - Backend: `cd backend; .venv\Scripts\python.exe -m uvicorn app.main:app --reload --reload-dir app --port 8000`
  - Frontend: `cd frontend; npm run dev`
- Then open **http://localhost:5173** and enter your PSN ID.

## Notes

- The first load of a large library is slow (the PSN API is per-game and rate-limited);
  it's cached for 24 hours afterwards.
- Trophy Advisor reads the configured NPSSO owner's active digital PS3/PS4/PS5
  entitlements, including games that have never been launched, and keeps cross-gen
  editions separate. Physical discs and inactive entitlements may not appear. It
  can enrich safe batches of up to 50 candidates with PSNProfiles tracked-owner,
  average trophy-completion, and platinum statistics, then rank them using the
  user's platinum-rate/platinum-achiever weights. The interface can continue through all
  filtered candidates as sequential bounded batches. Trial/Demo/Beta/test builds
  are excluded, already-earned platinum games are omitted using exact official
  trophy counts, and configured Gemini title or collection resolutions are cached
  for 180 days. Multi-list collections show each contained game's independent
  PSNProfiles signals instead of assigning a misleading aggregate score.
- The dashboard interface uses Traditional Chinese; game titles, trophy titles,
  and source-provided game/trophy text remain in their original language.
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
- PSNine links resolve the site's own title on first click, preferring its
  Simplified Chinese name and retaining English-only canonical titles such as
  `Tunic`, then open `https://www.psnine.com/psngame?title=<站內名稱>`.

## Tests

```powershell
cd backend; .venv\Scripts\python.exe -m pytest -q
```

## License

[MIT](LICENSE). Trophy data © Sony / PSNProfiles.
