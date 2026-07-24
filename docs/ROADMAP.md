# Trophy Hunter Dashboard — Roadmap / Next Steps

A status snapshot + what to do next, so a fresh session or contributor can pick
up without prior chat context. See also `docs/superpowers/specs/` (design) and
`docs/superpowers/plans/` (Phase-1 plan).

## Done (branch `redesign/modern-rebuild`)

- **Backend** (`backend/`, FastAPI): the token owner's OWN profile comes from the
  **official PSN API** (PSNAWP + NPSSO token in the repo-root `.env`) — trophies,
  rarity, earned dates (ISO), and **real playtime**. 24h profile cache + a
  **per-title trophy cache** keyed by each game's `last_updated`, so rebuilds only
  re-fetch recently-played games. PSNProfiles scraper kept as a (currently
  Cloudflare-blocked) secondary source. Endpoints: `GET /api/profile/{username}`
  (own id → PSN API, else scrape), `/api/profile/{username}/stream` (SSE),
  `/api/hltb`, `/api/health`. 23 pytest tests, pristine.
- **Frontend** (`frontend/`, Vite + React + TS + Tailwind, "Trophy Gold" theme):
  top-nav pages Overview / Games / Timeline / Milestones / Data. Real playtime
  tile + per-game playtime, per-game external links (PSNProfiles / PSNine / HLTB /
  Metacritic / Exophase), and HLTB completion times on game cards.
- **Run:** `./run.ps1` (Windows) → backend `:8000` + frontend `:5173`. First-time
  setup in `README.md`. Full `dakinwu20` cache pre-warmed: 165 titles / 5,286
  trophies.

## Next steps (prioritized)

### 1. PSNProfiles secondary source — unblock + re-parse (biggest open item)
- **Cloudflare IS beatable with `nodriver`** (undetected Chrome). Proven: it passed
  the "Just a moment" managed challenge and fetched gonz4lex's real profile HTML.
  (`cloudscraper`, `curl_cffi` TLS-impersonation, and Playwright headless **and**
  headed all fail — Playwright is detected via automation signals.)
- To actually use it:
  1. **Update the parser** — the site changed layout. `parse_profile_summary`'s
     selectors (`#user-bar`, `.username`, `li.total`, `Level`) are stale/absent in
     the current HTML. The trophy-log `table.zebra` is still present, so
     `parse_trophy_log_page` is closer. Capture a real page via nodriver, save it
     as a `backend/tests/fixtures/` fixture, and rewrite the summary parser.
  2. **Wire nodriver in** as the PSNProfiles fetch layer (it's async; headed → pops
     a Chrome window; slow per-page; solve the challenge once then reuse the
     browser/cookies). It's an arms race and may break when Cloudflare updates.
- Unblocks: other/public profiles, PSNProfiles rarity + trophy guides (est.
  platinum time / difficulty), and Metacritic/Exophase (same technique).

### 2. Smaller enhancements
- ~~Refresh button~~ — DONE: a manual "🔄 Refresh" button in the top nav force-refetches
  (`?refresh=true`, bypassing the 24h cache); per-title cache means only changed games re-fetch.
- **Fuzzy game-name match** for playtime — some titles don't show playtime because
  the `trophy_titles` name != `title_stats` name (e.g. Tunic). Normalize/fuzzy-match.
- **Cache `title_stats`** (short TTL) so cached rebuilds drop from ~30s to ~5s
  (it's the one remaining un-cached PSN call per rebuild).

### 3. Polish
- Lockfile (pip-tools/uv) for reproducible installs — there's a manual
  `starlette<1.0` pin in `backend/requirements.txt`.
- Tests for `psn_service` / `hltb_service`.
- Consider `filterwarnings = error` in `backend/pytest.ini`.

## Key facts for a fresh session
- PSN id: **`dakinwu20`**. NPSSO token lives in the **repo-root `.env`** (gitignored;
  `backend/app/config.py` reads the root `.env`).
- Cache dir: `backend/data_cache/` (absolute path in config; gitignored — a
  `git clean -fdx` would wipe it, then the first load re-warms slowly).
- Origin remote is the user's own repo `github.com/dakinwu/Trophy-Dashboard`;
  `upstream` is the original `gonz4lex/trophy-hunter-dashboard`.
