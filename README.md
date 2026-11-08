# Trophy Hunter Dashboard

A personal PlayStation trophy dashboard — rebuilt as a **FastAPI backend + React SPA**
(from the original Streamlit app by
[gonz4lex](https://github.com/gonz4lex/trophy-hunter-dashboard)).

Your **own** profile's data comes from the **official PlayStation Network API**
(via an NPSSO token): trophies, rarity, earned dates, and **real playtime**.
Other public profiles first use an official public summary when available,
then fall back to PSNProfiles through a visible nodriver-controlled Chrome
session. A public summary may not include individual trophy records or playtime.
This is an unofficial personal tool, not affiliated with Sony or the data sites.

**Local use only:** the backend has no multi-user authentication or authorization
layer. Do not expose it through a public host, tunnel or port forwarding. A public
source repository does not make this a safe public web service. Read
[SECURITY.md](SECURITY.md) before running or sharing data.

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
2. **Frontend** (Node **20.19+ on 20.x, or 22.12+**):
   ```powershell
   cd frontend
   npm ci
   ```
3. **PSN token** — copy `.env.example` to `.env` (in the repo root) and set `PSN_NPSSO`:
   - Log into playstation.com, then open
     `https://ca.account.sony.com/api/v1/ssocookie` and copy the `npsso` value.
   - `.env` is gitignored. Refresh the token when it expires; never share the
     token or the cookie response. An optional `backend/.env` overrides matching
     settings in the root `.env`, so check for old values there when debugging.
4. **Gemini title resolver (recommended for Trophy Advisor)** — add your Google
   AI Studio key to the same repo-root `.env` file:

   ```dotenv
   GEMINI_API_KEY=your-key-here
   GEMINI_GROUNDING_MODEL=gemini-2.5-flash
   ```

   The key remains backend-only. Advisor uses Gemini 2.5 Flash with Google Search
   grounding to resolve localized library titles to verified English PSNProfiles
   search terms and caches successful resolutions for 180 days. Name resolution
   does not guarantee that a matching trophy list exists for that platform.
   Existing English titles are cleaned locally without spending Gemini quota;
   up to 12 unresolved localized titles share one grounded Gemini request so a
   failed lookup cannot discard the rest of a large batch. Unknown
   multi-game collections use the same key with Google Search grounding on
   Gemini 2.5 Flash; one analysis batch shares one call, and results are cached
   for 180 days. Known collections are resolved locally without a Gemini call.
   One analysis action can therefore make multiple Gemini requests; it is not
   guaranteed to consume only one call. Without a key, local rules and existing
   caches still work, but some games cannot be resolved. Never put this key in
   a `VITE_*` variable. Stop the old services and restart `run.cmd` after changing
   `.env`.

## Run

- **Easiest — double-click `run.cmd`** in the project folder (File Explorer). It
  starts the backend (`:8001`) + frontend (`:5174`) in two windows and opens your
  dashboard's empty profile-search page in the browser. Enter your own PSN ID;
  no personal account is hardcoded. Close those two windows to stop the app.
  Missing frontend packages are synchronized before startup.
- From a terminal instead: `run.cmd`, or `./run.ps1` (PowerShell). The PowerShell
  launcher starts both services; open the frontend URL yourself.
- **Manual:**
  - Backend: `cd backend; .venv\Scripts\python.exe -m uvicorn app.main:app --reload --reload-dir app --port 8001`
  - Frontend: `cd frontend; npm run dev`
- Then open **http://localhost:5174** and enter your PSN ID.
- Backend health check: **http://localhost:8001/api/health**.
- Frontend source changes reload automatically; backend changes under `app/`
  trigger Uvicorn reload. Environment changes require restarting the services.
  Port 5174 is strict: startup fails if occupied instead of silently changing ports.

## Notes

- The first load of a large library is slow (the PSN API is per-game and rate-limited);
  it's cached for 24 hours afterwards.
- Trophy Advisor reads the configured NPSSO owner's active digital PS3/PS4/PS5
  entitlements, including games that have never been launched. Active claimed
  PS Plus entitlements may appear; this is **not the entire PS Plus catalogue**.
  Physical discs and inactive entitlements may not appear. It
  can enrich safe batches of up to 50 candidates with PSNProfiles tracked-owner,
  average trophy-completion, and platinum statistics, then rank them using the
  user's platinum-rate/platinum-achiever weights. The interface can continue through all
  filtered candidates as sequential bounded batches. Trial/Demo/Beta/test builds
  and known non-game apps, bonus content, artbooks and soundtracks are filtered
  using name rules and resolution results. Ambiguous names can still be missed.
  Already-earned platinum games are omitted using official trophy counts,
  and configured Gemini title or collection resolutions are cached
  for 180 days. Multi-list collections show each contained game's independent
  PSNProfiles signals instead of assigning a misleading aggregate score.
- The dashboard interface uses Traditional Chinese; game titles, trophy titles,
  and source-provided game/trophy text remain in their original language.
- A PSNProfiles cache miss may open Chrome. Cloudflare challenges can require
  manual verification; automated retries stop on a detected challenge rather
  than promising to bypass it. The first page can take a few minutes; the same
  browser session and cookies are reused for trophy-log pages.
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

## Advisor ranking, editions and recovery

- Default recommendation weights are **65% platinum rate + 35% platinum
  achievers**, adjustable in the interface. Achiever counts use logarithmic
  scaling relative to the highest count in the current data. If one metric is
  missing, only available metrics contribute; if both are missing, there is no
  score. General trophy completion is never substituted for platinum rate.
  Adding analysis results can change relative scores and ordering.
- Confirmed equivalent PS4/PS5 entitlements are merged using product/concept
  identity plus name checks, while retaining available platforms. The preferred
  edition prioritizes started progress, then progress/playtime, then PS5.
- PS4-platinum games can remain as PS5 opportunities only when the built-in
  catalogue confirms full or partial autopop (automatic trophy unlocks from
  transferred progress). Cards expose known status, source and verification date;
  unknown is not treated as confirmed support. This is not a live search of every
  game's current transfer behavior.
- Opening Advisor restores cached analysis; it does not re-analyze the entire
  library automatically. Individual failures are reported without discarding
  other games in the batch. A detected Cloudflare challenge stops automatic retries.
- Additional second-round Gemini title recovery is **off by default**. Backend
  requests must explicitly set `retry_title_lookup: true`; `allow_title_api: false`
  prevents title and collection API lookups for that batch.
- Trophy-list matching checks title, sequel information and platform. Previously
  successful, validated results can be retained when an update fails; cards label
  them as last-successful data pending an update and preserve their original
  fetch time. Old data is not silently presented as newly analyzed.

## Cache and trophy artwork

The default cache directory is `backend/data_cache/`. **Reloading the browser or
restarting the services does not clear these files.** Backend cache lifetimes:

| Data | Lifetime / behavior |
| --- | --- |
| Profile, Advisor library, platinum gallery | 24 hours |
| Individual game's trophy details | 6 hours |
| PSNProfiles trophy lists and analysis statistics | 30 days; validated last-successful data may be retained as stale |
| PSNProfiles guide difficulty / platinum time | 90 days, on demand |
| PSNProfiles world / country rank | 6 hours, on demand |
| Gemini titles, collection resolutions, PSNine titles | 180 days |
| Downloaded official trophy artwork | No expiry; stored locally |

These are backend lifetimes; frontend queries have their own caching and loading
triggers. Expiry permits a future lookup to update data, not a background schedule
that automatically crawls everything. Refreshing a profile does not clear all
Advisor analysis caches. For example, reloading immediately after a successful
analysis should reuse that result rather than spend Gemini quota again.

The platinum gallery uses a separate official platinum-title list, independent of
an incomplete trophy log. Official trophy images are validated and stored as
original image bytes under `backend/data_cache/trophy_images/`, then served through
the backend. New images still need a working source and network; downloaded files
remain available locally. Missing originals are marked unavailable, not replaced
with a generic trophy presented as the original. Public-summary-only profiles may
use game covers instead of individual trophy artwork or earned dates.

## Troubleshooting and limits

- **Cannot read the library:** verify that the selected profile owns the configured
  NPSSO token, check that the token is valid, then restart the backend after updating it.
- **Loading appears stuck / Chrome remains open:** inspect the service windows and
  `backend/logs/` for a challenge, timeout or source error. Avoid starting several
  full-library analyses concurrently.
- **PSNProfiles N/A:** data for the correct edition, DLC or trophy may be unavailable
  or unmatched. The official rate is not substituted as a fake PSNProfiles rate.
- **Analysis failure:** a resolved English title can still fail platform matching
  or external-site access; check the individual error and logs rather than assuming
  every failure is a Gemini failure.
- **Missing image:** an uncached original still requires accessible official data.
  Do not delete the entire cache just to retry a single image.

`.env`, `backend/data_cache/` and `backend/logs/` are excluded from Git. Review and
redact account information, credentials and other private data before sharing logs.
Local assistant settings, private planning notes, dependencies, build output and
test artifacts are also ignored. Source code, dependency lockfiles, anonymized
test fixtures, public documentation and the original license remain tracked.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the development workflow and
[docs/ROADMAP.md](docs/ROADMAP.md) for current scope and follow-up work.

## Validation

Frontend (`build` includes TypeScript checking):

```powershell
cd frontend
npm run lint
npm run build
```

Backend:

```powershell
cd backend; .venv\Scripts\python.exe -m pytest -q
```

There are currently no separate frontend `test` or `typecheck` scripts. Passing
automated tests does not mean every game's live external-site data was verified.

## License

[MIT](LICENSE). Original project attribution is retained. Game, image and trophy
data rights belong to their respective owners.
