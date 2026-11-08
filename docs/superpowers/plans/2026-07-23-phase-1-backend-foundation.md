# Phase 1 — Backend Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up a FastAPI backend that scrapes a public PSNProfiles profile (summary + full trophy log), caches it for 24h, and serves it over a REST API with an SSE progress stream — reusing the existing scraper logic and adding the test coverage it currently lacks.

**Architecture:** A `backend/` package with `app/` (FastAPI app, config, Pydantic models, API routers, scraping services, file cache) and `tests/`. Parsing functions are pure (HTML string → typed models) and unit-tested against fixtures. Scraping functions take an injectable `session` (as the current code already does), so tests use a `FakeSession` with no network. A thin service ties cache + scrape together; API endpoints expose it.

**Tech Stack:** Python 3.10+, FastAPI, Uvicorn, Pydantic v2, pydantic-settings, cloudscraper, BeautifulSoup4, sse-starlette, pytest, httpx (TestClient).

## Global Constraints

- Python **3.10+** (plan uses `X | None` union syntax).
- Backend lives in `backend/`; source under `backend/app/`, tests under `backend/tests/`. **Run `pytest` and `uvicorn` from the `backend/` directory** (a `pytest.ini` sets `pythonpath = .`).
- **Reuse the existing PSNProfiles parsing selectors verbatim** from [core/scraper.py](../../../core/scraper.py) — do not change which CSS classes / cell indices are parsed.
- Keep polite scrape delays (`random.uniform(1.0, 2.5)` seconds) between real page fetches. **Tests monkeypatch `time.sleep`** so they run instantly.
- **Never commit secrets.** `.env` is already gitignored. All config is read via `app.config.settings` (backed by `.env`).
- Profile cache TTL = **24 hours**.
- Frequent commits, conventional commit messages (`feat:`, `test:`, `chore:`).
- This is **Phase 1 of 5**. Later phases (frontend, enrichment, PSN real playtime, polish) get their own plans. Design decisions here must not block them (e.g., cache is written generically so enrichment can add other TTLs later).

---

## File Structure (Phase 1)

```
backend/
  requirements.txt          # runtime + test deps
  pytest.ini                # pythonpath=., testpaths=tests
  .env.example              # documents PSN_NPSSO etc. (no real values)
  app/
    __init__.py
    main.py                 # create_app(): FastAPI + CORS + routers
    config.py               # Settings (pydantic-settings) -> settings
    models.py               # TrophyCounts, ProfileSummary, Trophy, ProfileData
    api/
      __init__.py
      meta.py               # GET /api/health
      profile.py            # GET /api/profile/{username}, /api/profile/{username}/stream
    services/
      __init__.py
      http.py               # create_session() -> cloudscraper session
      psnprofiles.py        # parse_* (pure) + fetch_* + scrape_profile (session injected)
      profile_service.py    # get_profile(): cache + scrape orchestration
    core/
      __init__.py
      cache.py              # FileCache(base_dir).load(key, ttl)/save(key, data)
  tests/
    __init__.py
    conftest.py             # FakeResponse, FakeSession, load_fixture()
    fixtures/
      profile_summary.html
      trophy_log_page.html
    test_api_meta.py
    test_psnprofiles_parsing.py
    test_scrape.py
    test_cache.py
    test_profile_service.py
    test_api_profile.py
    test_api_stream.py
```

---

### Task 1: Backend scaffold, config, and health endpoint

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/pytest.ini`
- Create: `backend/.env.example`
- Create: `backend/app/__init__.py` (empty)
- Create: `backend/app/config.py`
- Create: `backend/app/api/__init__.py` (empty)
- Create: `backend/app/api/meta.py`
- Create: `backend/app/main.py`
- Create: `backend/tests/__init__.py` (empty)
- Test: `backend/tests/test_api_meta.py`

**Interfaces:**
- Produces: `app.config.settings` with attributes `psn_npsso: str | None`, `cache_dir: str`, `cors_origins: list[str]`, `scrape_user_agent: str`. `app.main.create_app() -> FastAPI` and module-level `app`. `app.api.meta.router` mounted under `/api`.

- [ ] **Step 1: Create `backend/requirements.txt`**

```
fastapi>=0.110
uvicorn[standard]>=0.29
pydantic>=2.6
pydantic-settings>=2.2
cloudscraper>=1.2.71
beautifulsoup4>=4.12
requests>=2.31
sse-starlette>=2.1
pytest>=8.0
httpx>=0.27
```

- [ ] **Step 2: Install dependencies**

From the `backend/` directory, using a virtualenv (PowerShell shown; the repo already has a `.venv` you may reuse, or create `backend/.venv`):

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Expected: all packages install without error.

- [ ] **Step 3: Create `backend/pytest.ini`**

```ini
[pytest]
pythonpath = .
testpaths = tests
```

- [ ] **Step 4: Create `backend/.env.example`**

```
# Copy to .env (which is gitignored) and fill in real values.
# PSN NPSSO token — get it by logging into playstation.com, then visiting
# https://ca.account.sony.com/api/v1/ssocookie and copying the "npsso" value.
PSN_NPSSO=
# Where cached JSON is written (relative to backend/).
CACHE_DIR=data_cache
# Allowed frontend origins for CORS (JSON list).
CORS_ORIGINS=["http://localhost:5174"]
```

- [ ] **Step 5: Create `backend/app/config.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    psn_npsso: str | None = None
    cache_dir: str = "data_cache"
    cors_origins: list[str] = ["http://localhost:5174"]
    scrape_user_agent: str = "TrophyHunter/2.0 (local; hello@example.com)"


settings = Settings()
```

- [ ] **Step 6: Create `backend/app/api/meta.py`**

```python
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 7: Create `backend/app/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api import meta


def create_app() -> FastAPI:
    app = FastAPI(title="Trophy Hunter API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(meta.router, prefix="/api")
    return app


app = create_app()
```

- [ ] **Step 8: Create empty package files**

Create `backend/app/__init__.py`, `backend/app/api/__init__.py`, and `backend/tests/__init__.py`, each empty.

- [ ] **Step 9: Write the failing test — `backend/tests/test_api_meta.py`**

```python
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
```

- [ ] **Step 10: Run test to verify it passes**

Run (from `backend/`): `pytest tests/test_api_meta.py -v`
Expected: PASS (`test_health_returns_ok`).

- [ ] **Step 11: Commit**

```bash
git add backend/
git commit -m "feat(backend): scaffold FastAPI app with config and health endpoint"
```

---

### Task 2: Data models

**Files:**
- Create: `backend/app/models.py`
- Test: `backend/tests/test_psnprofiles_parsing.py` (created here; parser assertions added in Task 3)

**Interfaces:**
- Produces:
  - `TrophyCounts(total:int=0, platinum:int=0, gold:int=0, silver:int=0, bronze:int=0)`
  - `ProfileSummary(username:str, avatar_url:str|None=None, total_trophies:TrophyCounts=..., stats:dict[str,str]={})`
  - `Trophy(game:str, icon_url:str, title:str, timestamp:str, rarity_percent:str, grade:str)`
  - `ProfileData(profile_summary:ProfileSummary, trophy_log:list[Trophy])`

- [ ] **Step 1: Write the failing test — `backend/tests/test_psnprofiles_parsing.py`**

```python
from app.models import TrophyCounts, ProfileSummary, Trophy, ProfileData


def test_models_construct_and_roundtrip():
    summary = ProfileSummary(
        username="TestUser",
        avatar_url="https://example.com/a.png",
        total_trophies=TrophyCounts(total=1234, platinum=10, gold=50, silver=300, bronze=874),
        stats={"Level": "42"},
    )
    trophy = Trophy(
        game="Test Game",
        icon_url="https://example.com/t.png",
        title="First Blood",
        timestamp="6th Jul 2024 10:11:23 pm",
        rarity_percent="2.5%",
        grade="Gold",
    )
    data = ProfileData(profile_summary=summary, trophy_log=[trophy])
    dumped = data.model_dump()
    restored = ProfileData.model_validate(dumped)
    assert restored.profile_summary.total_trophies.total == 1234
    assert restored.trophy_log[0].grade == "Gold"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_psnprofiles_parsing.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.models'`.

- [ ] **Step 3: Create `backend/app/models.py`**

```python
from pydantic import BaseModel, Field


class TrophyCounts(BaseModel):
    total: int = 0
    platinum: int = 0
    gold: int = 0
    silver: int = 0
    bronze: int = 0


class ProfileSummary(BaseModel):
    username: str
    avatar_url: str | None = None
    total_trophies: TrophyCounts = Field(default_factory=TrophyCounts)
    stats: dict[str, str] = Field(default_factory=dict)


class Trophy(BaseModel):
    game: str
    icon_url: str
    title: str
    timestamp: str
    rarity_percent: str
    grade: str


class ProfileData(BaseModel):
    profile_summary: ProfileSummary
    trophy_log: list[Trophy] = Field(default_factory=list)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_psnprofiles_parsing.py -v`
Expected: PASS (`test_models_construct_and_roundtrip`).

- [ ] **Step 5: Commit**

```bash
git add backend/app/models.py backend/tests/test_psnprofiles_parsing.py
git commit -m "feat(backend): add Pydantic models for profile and trophy data"
```

---

### Task 3: Pure HTML parsers (summary + trophy log)

**Files:**
- Create: `backend/app/services/__init__.py` (empty)
- Create: `backend/app/services/psnprofiles.py` (parsers only in this task)
- Create: `backend/tests/fixtures/profile_summary.html`
- Create: `backend/tests/fixtures/trophy_log_page.html`
- Create: `backend/tests/conftest.py`
- Modify: `backend/tests/test_psnprofiles_parsing.py` (add parser tests)

**Interfaces:**
- Consumes: `app.models.ProfileSummary`, `TrophyCounts`, `Trophy`.
- Produces:
  - `parse_profile_summary(html: str) -> ProfileSummary | None`
  - `parse_trophy_log_page(html: str) -> list[Trophy]`

- [ ] **Step 1: Create fixture `backend/tests/fixtures/profile_summary.html`**

```html
<html><body>
<div id="user-bar">
  <div class="avatar"><img src="https://example.com/avatar.png"></div>
  <span class="username">TestUser</span>
  <ul>
    <li class="total">1,234</li>
    <li class="platinum">10</li>
    <li class="gold">50</li>
    <li class="silver">300</li>
    <li class="bronze">874</li>
  </ul>
</div>
<div class="stats">
  <span class="stat">42<span>Level</span></span>
  <span class="stat">99.9%<span>Completion</span></span>
</div>
</body></html>
```

- [ ] **Step 2: Create fixture `backend/tests/fixtures/trophy_log_page.html`**

```html
<html><body>
<table class="zebra">
  <tr>
    <th>Game</th><th>Trophy</th><th>Title</th><th>x</th><th>x</th>
    <th>Date</th><th>x</th><th>x</th><th>Rarity</th><th>Grade</th>
  </tr>
  <tr>
    <td><img title="Test Game" src="https://example.com/game.png"></td>
    <td><img src="https://example.com/trophy.png"></td>
    <td><a class="title">First Blood</a></td>
    <td></td>
    <td></td>
    <td><span class="typo-top-date">6th Jul 2024</span><span class="typo-bottom-date">10:11:23 pm</span></td>
    <td></td>
    <td></td>
    <td><span class="typo-top">2.5%</span></td>
    <td><img title="Gold"></td>
  </tr>
</table>
</body></html>
```

- [ ] **Step 3: Create `backend/tests/conftest.py`**

```python
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class FakeResponse:
    def __init__(self, text: str = "", status_code: int = 200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400 and self.status_code != 404:
            import requests
            raise requests.exceptions.HTTPError(f"status {self.status_code}")


class FakeSession:
    """Mimics the subset of a requests/cloudscraper session the scraper uses."""

    def __init__(self, summary_html: str = "", log_pages: list[str] | None = None):
        self.summary_html = summary_html
        self.log_pages = list(log_pages or [])
        self.headers: dict[str, str] = {}
        self._page_idx = 0

    def get(self, url: str, timeout: float | None = None) -> FakeResponse:
        if "/log?page=" in url:
            if self._page_idx < len(self.log_pages):
                html = self.log_pages[self._page_idx]
                self._page_idx += 1
                return FakeResponse(html, 200)
            return FakeResponse("", 404)
        return FakeResponse(self.summary_html, 200)
```

- [ ] **Step 4: Add failing parser tests to `backend/tests/test_psnprofiles_parsing.py`**

Append:

```python
from tests.conftest import load_fixture
from app.services.psnprofiles import parse_profile_summary, parse_trophy_log_page


def test_parse_profile_summary_extracts_fields():
    summary = parse_profile_summary(load_fixture("profile_summary.html"))
    assert summary is not None
    assert summary.username == "TestUser"
    assert summary.avatar_url == "https://example.com/avatar.png"
    assert summary.total_trophies.total == 1234
    assert summary.total_trophies.platinum == 10
    assert summary.stats["Level"] == "42"


def test_parse_profile_summary_returns_none_on_garbage():
    assert parse_profile_summary("<html><body>nope</body></html>") is None


def test_parse_trophy_log_page_extracts_rows():
    trophies = parse_trophy_log_page(load_fixture("trophy_log_page.html"))
    assert len(trophies) == 1
    t = trophies[0]
    assert t.game == "Test Game"
    assert t.title == "First Blood"
    assert t.timestamp == "6th Jul 2024 10:11:23 pm"
    assert t.rarity_percent == "2.5%"
    assert t.grade == "Gold"


def test_parse_trophy_log_page_empty_when_no_table():
    assert parse_trophy_log_page("<html><body></body></html>") == []
```

- [ ] **Step 5: Run tests to verify they fail**

Run: `pytest tests/test_psnprofiles_parsing.py -v`
Expected: the parser tests FAIL with `ImportError: cannot import name 'parse_profile_summary'`.

- [ ] **Step 6: Create `backend/app/services/psnprofiles.py` (parsers)**

Ported faithfully from [core/scraper.py](../../../core/scraper.py), returning models. Same selectors/cell indices.

```python
import logging
from bs4 import BeautifulSoup

from app.models import ProfileSummary, TrophyCounts, Trophy

logger = logging.getLogger(__name__)


def parse_profile_summary(html_content: str) -> ProfileSummary | None:
    soup = BeautifulSoup(html_content, "html.parser")
    try:
        user_bar = soup.find("div", id="user-bar")
        if not user_bar:
            return None

        username_span = user_bar.find("span", class_="username")
        username = username_span.text.strip() if username_span else None
        if not username:
            return None

        avatar_url = None
        avatar_div = user_bar.find("div", class_="avatar")
        if avatar_div:
            avatar_img = avatar_div.find("img")
            if avatar_img and avatar_img.has_attr("src"):
                avatar_url = avatar_img["src"]

        counts = TrophyCounts()
        for t_type in ["total", "platinum", "gold", "silver", "bronze"]:
            el = user_bar.find("li", class_=t_type)
            if el:
                setattr(counts, t_type, int(el.text.strip().replace(",", "")))

        stats: dict[str, str] = {}
        stats_div = soup.find("div", class_="stats")
        if stats_div:
            for stat in stats_div.find_all("span", class_="stat"):
                value = stat.contents[0].strip().replace(",", "")
                label_span = stat.find("span")
                if label_span:
                    stats[label_span.text.strip()] = value

        return ProfileSummary(
            username=username,
            avatar_url=avatar_url,
            total_trophies=counts,
            stats=stats,
        )
    except (AttributeError, TypeError, ValueError) as e:
        logger.error("Error parsing summary: %s", e)
        return None


def parse_trophy_log_page(html_content: str) -> list[Trophy]:
    soup = BeautifulSoup(html_content, "html.parser")
    trophies: list[Trophy] = []
    trophy_table = soup.find("table", class_="zebra")
    if not trophy_table:
        return []

    for row in trophy_table.find_all("tr"):
        try:
            cells = row.find_all("td")
            if len(cells) < 10:
                continue

            game_img = cells[0].find("img")
            trophy_img = cells[1].find("img")
            title_anchor = cells[2].find("a", class_="title")
            date_span = cells[5].find("span", class_="typo-top-date")
            time_span = cells[5].find("span", class_="typo-bottom-date")
            rarity_span = cells[8].find("span", class_="typo-top")
            grade_img = cells[9].find("img")

            date_str = date_span.text.strip() if date_span else ""
            time_str = time_span.text.strip() if time_span else ""

            trophies.append(
                Trophy(
                    game=game_img["title"] if game_img else "N/A",
                    icon_url=trophy_img["src"] if trophy_img else "N/A",
                    title=title_anchor.text.strip() if title_anchor else "N/A",
                    timestamp=f"{date_str} {time_str}".strip(),
                    rarity_percent=rarity_span.text.strip() if rarity_span else "N/A",
                    grade=grade_img["title"] if grade_img else "N/A",
                )
            )
        except (AttributeError, TypeError, KeyError) as e:
            logger.warning("Skipping malformed row in trophy log: %s", e)
            continue

    return trophies
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `pytest tests/test_psnprofiles_parsing.py -v`
Expected: PASS (all 5 tests, including the model roundtrip from Task 2).

- [ ] **Step 8: Commit**

```bash
git add backend/app/services/ backend/tests/
git commit -m "feat(backend): port PSNProfiles HTML parsers with fixture tests"
```

---

### Task 4: Scraping orchestration (session-injected)

**Files:**
- Modify: `backend/app/services/psnprofiles.py` (add fetch/scrape functions)
- Create: `backend/tests/test_scrape.py`

**Interfaces:**
- Consumes: `parse_profile_summary`, `parse_trophy_log_page`, `app.models.ProfileData`.
- Produces:
  - `PSN_BASE = "https://psnprofiles.com"`
  - `fetch_summary(session, base_url: str) -> ProfileSummary | None`
  - `fetch_trophy_log(session, base_url: str, on_progress=None, should_stop=None) -> list[Trophy]` where `on_progress: Callable[[int], None]` (called with the page number just fetched) and `should_stop: Callable[[], bool] | None`.
  - `scrape_profile(session, username: str, on_progress=None, should_stop=None) -> ProfileData | None` where `on_progress: Callable[[int, int], None]` (called with `(page, total_pages)`).

- [ ] **Step 1: Write failing tests — `backend/tests/test_scrape.py`**

```python
import math

from tests.conftest import FakeSession, load_fixture
from app.services import psnprofiles


def _session_with(pages: int) -> FakeSession:
    log_html = load_fixture("trophy_log_page.html")
    return FakeSession(
        summary_html=load_fixture("profile_summary.html"),
        log_pages=[log_html] * pages,
    )


def test_fetch_summary_parses(monkeypatch):
    session = _session_with(0)
    summary = psnprofiles.fetch_summary(session, "https://psnprofiles.com/TestUser")
    assert summary is not None
    assert summary.total_trophies.total == 1234


def test_fetch_trophy_log_paginates_until_404(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)
    session = _session_with(3)
    seen_pages: list[int] = []
    log = psnprofiles.fetch_trophy_log(
        session,
        "https://psnprofiles.com/TestUser",
        on_progress=lambda page: seen_pages.append(page),
    )
    assert len(log) == 3            # one trophy per fixture page, 3 pages
    assert seen_pages == [1, 2, 3]


def test_fetch_trophy_log_respects_should_stop(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)
    session = _session_with(5)
    calls = {"n": 0}

    def should_stop() -> bool:
        calls["n"] += 1
        return calls["n"] > 2       # allow ~2 iterations then stop

    log = psnprofiles.fetch_trophy_log(
        session, "https://psnprofiles.com/TestUser", should_stop=should_stop
    )
    assert len(log) <= 2


def test_scrape_profile_reports_total_pages(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)
    session = _session_with(2)
    progress: list[tuple[int, int]] = []
    data = psnprofiles.scrape_profile(
        session, "TestUser", on_progress=lambda page, total: progress.append((page, total))
    )
    assert data is not None
    assert len(data.trophy_log) == 2
    expected_total = math.ceil(1234 / 50)
    assert progress[0] == (1, expected_total)


def test_scrape_profile_returns_none_for_missing(monkeypatch):
    session = FakeSession(summary_html="<html><body>nope</body></html>")
    assert psnprofiles.scrape_profile(session, "Ghost") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_scrape.py -v`
Expected: FAIL with `AttributeError: module 'app.services.psnprofiles' has no attribute 'fetch_summary'`.

- [ ] **Step 3: Append scraping functions to `backend/app/services/psnprofiles.py`**

Add these imports at the top of the file (merge with existing imports):

```python
import math
import random
import time
from typing import Callable

from app.models import ProfileData
```

Then append:

```python
PSN_BASE = "https://psnprofiles.com"


def fetch_summary(session, base_url: str) -> ProfileSummary | None:
    rs = session.get(base_url, timeout=15)
    rs.raise_for_status()
    return parse_profile_summary(rs.text)


def fetch_trophy_log(
    session,
    base_url: str,
    on_progress: Callable[[int], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> list[Trophy]:
    all_trophies: list[Trophy] = []
    page = 1
    session.headers.update({"Referer": base_url})

    while should_stop is None or not should_stop():
        rs = session.get(f"{base_url}/log?page={page}", timeout=15)
        if rs.status_code == 404:
            break
        rs.raise_for_status()

        trophies = parse_trophy_log_page(rs.text)
        if not trophies:
            break

        all_trophies.extend(trophies)
        if on_progress:
            on_progress(page)
        page += 1
        time.sleep(random.uniform(1.0, 2.5))

    return all_trophies


def scrape_profile(
    session,
    username: str,
    on_progress: Callable[[int, int], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> ProfileData | None:
    base_url = f"{PSN_BASE}/{username}"
    summary = fetch_summary(session, base_url)
    if summary is None or summary.total_trophies.total == 0:
        return None

    total_pages = max(1, math.ceil(summary.total_trophies.total / 50))

    def _page_progress(page: int) -> None:
        if on_progress:
            on_progress(page, total_pages)

    log = fetch_trophy_log(
        session, base_url, on_progress=_page_progress, should_stop=should_stop
    )
    return ProfileData(profile_summary=summary, trophy_log=log)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_scrape.py -v`
Expected: PASS (all 5 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/psnprofiles.py backend/tests/test_scrape.py
git commit -m "feat(backend): add session-injected scrape orchestration with progress/stop"
```

---

### Task 5: Layered-TTL file cache

**Files:**
- Create: `backend/app/core/__init__.py` (empty)
- Create: `backend/app/core/cache.py`
- Create: `backend/tests/test_cache.py`

**Interfaces:**
- Produces: `FileCache(base_dir: str | Path)` with `.load(key: str, ttl_seconds: float) -> dict | None` and `.save(key: str, data: dict) -> None`. Keys may contain `/` (namespaced, e.g. `profile/testuser`); the cache maps them to safe filenames.

- [ ] **Step 1: Write failing tests — `backend/tests/test_cache.py`**

```python
import os
import time

from app.core.cache import FileCache


def test_save_then_load_hits_within_ttl(tmp_path):
    cache = FileCache(tmp_path)
    cache.save("profile/testuser", {"a": 1})
    assert cache.load("profile/testuser", ttl_seconds=1000) == {"a": 1}


def test_load_miss_when_absent(tmp_path):
    cache = FileCache(tmp_path)
    assert cache.load("profile/nobody", ttl_seconds=1000) is None


def test_load_miss_when_expired(tmp_path):
    cache = FileCache(tmp_path)
    cache.save("profile/testuser", {"a": 1})
    # Backdate the file's mtime by 2 hours.
    path = cache._path("profile/testuser")
    old = time.time() - 7200
    os.utime(path, (old, old))
    assert cache.load("profile/testuser", ttl_seconds=3600) is None


def test_key_with_slash_is_namespaced(tmp_path):
    cache = FileCache(tmp_path)
    cache.save("enrichment/hltb/god-of-war", {"main": 20})
    assert cache.load("enrichment/hltb/god-of-war", ttl_seconds=1000) == {"main": 20}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cache.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.core.cache'`.

- [ ] **Step 3: Create `backend/app/core/__init__.py` (empty) and `backend/app/core/cache.py`**

```python
import json
import time
from pathlib import Path


class FileCache:
    """JSON file cache with a per-load TTL, so different data types can use
    different freshness windows against the same store."""

    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        safe = key.replace("/", "__")
        return self.base_dir / f"{safe}.json"

    def load(self, key: str, ttl_seconds: float) -> dict | None:
        path = self._path(key)
        if not path.exists():
            return None
        if (time.time() - path.stat().st_mtime) > ttl_seconds:
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def save(self, key: str, data: dict) -> None:
        self._path(key).write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_cache.py -v`
Expected: PASS (all 4 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/ backend/tests/test_cache.py
git commit -m "feat(backend): add layered-TTL JSON file cache"
```

---

### Task 6: Profile service + REST endpoint

**Files:**
- Create: `backend/app/services/http.py`
- Create: `backend/app/services/profile_service.py`
- Create: `backend/app/api/profile.py`
- Modify: `backend/app/main.py` (mount profile router)
- Create: `backend/tests/test_profile_service.py`
- Create: `backend/tests/test_api_profile.py`

**Interfaces:**
- Consumes: `FileCache`, `psnprofiles.scrape_profile`, `settings`, `ProfileData`.
- Produces:
  - `app.services.http.create_session() -> session` (cloudscraper session with User-Agent from settings).
  - `app.services.profile_service.PROFILE_TTL = 86400` and `get_profile(username: str, *, force: bool = False, on_progress=None, should_stop=None, session=None, cache=None) -> ProfileData | None`.
  - `app.api.profile.router`: `GET /api/profile/{username}?refresh=<bool>` → `ProfileData` JSON (200), 404 if missing/private, 502 on upstream network error.

- [ ] **Step 1: Create `backend/app/services/http.py`**

```python
import cloudscraper

from app.config import settings


def create_session():
    session = cloudscraper.create_scraper()
    session.headers.update({"User-Agent": settings.scrape_user_agent})
    return session
```

- [ ] **Step 2: Create `backend/app/services/profile_service.py`**

```python
from typing import Callable

from app.config import settings
from app.core.cache import FileCache
from app.models import ProfileData
from app.services import psnprofiles
from app.services.http import create_session

PROFILE_TTL = 86400  # 24 hours


def get_profile(
    username: str,
    *,
    force: bool = False,
    on_progress: Callable[[int, int], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
    session=None,
    cache: FileCache | None = None,
) -> ProfileData | None:
    cache = cache or FileCache(settings.cache_dir)
    key = f"profile/{username.lower()}"

    if not force:
        cached = cache.load(key, PROFILE_TTL)
        if cached is not None:
            return ProfileData.model_validate(cached)

    session = session or create_session()
    data = psnprofiles.scrape_profile(
        session, username, on_progress=on_progress, should_stop=should_stop
    )
    if data is None:
        return None

    cache.save(key, data.model_dump())
    return data
```

- [ ] **Step 3: Create `backend/app/api/profile.py`**

```python
import requests
from fastapi import APIRouter, HTTPException, Query

from app.services.profile_service import get_profile

router = APIRouter()


@router.get("/profile/{username}")
def read_profile(username: str, refresh: bool = Query(False)):
    try:
        data = get_profile(username, force=refresh)
    except requests.exceptions.RequestException:
        raise HTTPException(status_code=502, detail="Error fetching profile from PSNProfiles.")
    if data is None:
        raise HTTPException(status_code=404, detail=f"Profile '{username}' not found or is private.")
    return data.model_dump()
```

- [ ] **Step 4: Mount the profile router in `backend/app/main.py`**

Change the imports and `create_app` body:

```python
from app.api import meta, profile
```

and, after the `meta` router include, add:

```python
    app.include_router(profile.router, prefix="/api")
```

- [ ] **Step 5: Write failing test — `backend/tests/test_profile_service.py`**

```python
from tests.conftest import FakeSession, load_fixture
from app.core.cache import FileCache
from app.services import profile_service


def _session(pages: int) -> FakeSession:
    return FakeSession(
        summary_html=load_fixture("profile_summary.html"),
        log_pages=[load_fixture("trophy_log_page.html")] * pages,
    )


def test_get_profile_scrapes_and_caches(tmp_path, monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)
    cache = FileCache(tmp_path)
    data = profile_service.get_profile("TestUser", session=_session(2), cache=cache)
    assert data is not None
    assert len(data.trophy_log) == 2
    # Cached file exists and a second call (with a session that would yield
    # nothing) still returns cached data.
    again = profile_service.get_profile("TestUser", session=FakeSession(), cache=cache)
    assert again is not None
    assert len(again.trophy_log) == 2


def test_get_profile_force_bypasses_cache(tmp_path, monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)
    cache = FileCache(tmp_path)
    profile_service.get_profile("TestUser", session=_session(2), cache=cache)
    forced = profile_service.get_profile(
        "TestUser", force=True, session=_session(3), cache=cache
    )
    assert forced is not None
    assert len(forced.trophy_log) == 3


def test_get_profile_none_for_missing(tmp_path):
    cache = FileCache(tmp_path)
    data = profile_service.get_profile(
        "Ghost", session=FakeSession(summary_html="<html></html>"), cache=cache
    )
    assert data is None
```

- [ ] **Step 6: Write failing test — `backend/tests/test_api_profile.py`**

```python
from fastapi.testclient import TestClient

from app.main import app
from app.models import ProfileData, ProfileSummary, TrophyCounts, Trophy
import app.api.profile as profile_api

client = TestClient(app)


def _sample() -> ProfileData:
    return ProfileData(
        profile_summary=ProfileSummary(
            username="TestUser", total_trophies=TrophyCounts(total=1)
        ),
        trophy_log=[
            Trophy(game="G", icon_url="u", title="T", timestamp="ts", rarity_percent="1%", grade="Gold")
        ],
    )


def test_get_profile_200(monkeypatch):
    monkeypatch.setattr(profile_api, "get_profile", lambda username, force=False: _sample())
    resp = client.get("/api/profile/TestUser")
    assert resp.status_code == 200
    assert resp.json()["profile_summary"]["username"] == "TestUser"
    assert len(resp.json()["trophy_log"]) == 1


def test_get_profile_404(monkeypatch):
    monkeypatch.setattr(profile_api, "get_profile", lambda username, force=False: None)
    resp = client.get("/api/profile/Ghost")
    assert resp.status_code == 404
```

- [ ] **Step 7: Run tests to verify they fail, then pass after Steps 1–4**

Run: `pytest tests/test_profile_service.py tests/test_api_profile.py -v`
Expected: PASS once `http.py`, `profile_service.py`, `profile.py`, and the `main.py` mount from Steps 1–4 are in place. (If you wrote tests first, they FAIL with import/attribute errors before those files exist.)

- [ ] **Step 8: Commit**

```bash
git add backend/app/services/http.py backend/app/services/profile_service.py \
        backend/app/api/profile.py backend/app/main.py \
        backend/tests/test_profile_service.py backend/tests/test_api_profile.py
git commit -m "feat(backend): add profile service (cache+scrape) and REST endpoint"
```

---

### Task 7: SSE progress stream endpoint

**Files:**
- Modify: `backend/app/api/profile.py` (add stream endpoint)
- Create: `backend/tests/test_api_stream.py`

**Interfaces:**
- Consumes: `get_profile` (with its `on_progress(page, total)` callback), `sse_starlette.sse.EventSourceResponse`.
- Produces: `GET /api/profile/{username}/stream` — an `text/event-stream` emitting:
  - `event: progress`, `data: {"page": N, "total": M}` per page,
  - then either `event: done`, `data: {"found": true|false}` or `event: error`, `data: {"error": "..."}`.

- [ ] **Step 1: Write failing test — `backend/tests/test_api_stream.py`**

```python
import json

from fastapi.testclient import TestClient

from app.main import app
from app.models import ProfileData, ProfileSummary, TrophyCounts
import app.api.profile as profile_api

client = TestClient(app)


def test_stream_emits_progress_then_done(monkeypatch):
    def fake_get_profile(username, *, force=False, on_progress=None, should_stop=None):
        if on_progress:
            on_progress(1, 2)
            on_progress(2, 2)
        return ProfileData(
            profile_summary=ProfileSummary(username=username, total_trophies=TrophyCounts(total=1))
        )

    monkeypatch.setattr(profile_api, "get_profile", fake_get_profile)

    with client.stream("GET", "/api/profile/TestUser/stream") as resp:
        assert resp.status_code == 200
        body = "".join(resp.iter_text())

    assert "event: progress" in body
    assert '"page": 1' in body
    assert '"total": 2' in body
    assert "event: done" in body
    assert '"found": true' in body
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_api_stream.py -v`
Expected: FAIL (404 — route not defined yet).

- [ ] **Step 3: Add the stream endpoint to `backend/app/api/profile.py`**

Add imports at the top (merge with existing):

```python
import asyncio
import json
from sse_starlette.sse import EventSourceResponse
```

Append:

```python
@router.get("/profile/{username}/stream")
async def stream_profile(username: str):
    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def on_progress(page: int, total: int) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, {"type": "progress", "page": page, "total": total})

    async def run() -> None:
        try:
            data = await asyncio.to_thread(
                get_profile, username, force=True, on_progress=on_progress
            )
            loop.call_soon_threadsafe(
                queue.put_nowait, {"type": "done", "found": data is not None}
            )
        except Exception as exc:  # surfaced to the client as an error event
            loop.call_soon_threadsafe(queue.put_nowait, {"type": "error", "error": str(exc)})

    async def event_gen():
        task = asyncio.create_task(run())
        try:
            while True:
                msg = await queue.get()
                kind = msg.pop("type")
                yield {"event": kind, "data": json.dumps(msg)}
                if kind in ("done", "error"):
                    break
        finally:
            await task

    return EventSourceResponse(event_gen())
```

Note: `get_profile` is already imported in this module (Task 6). The stream always forces a fresh scrape so progress is meaningful; the completed data is read afterward via `GET /api/profile/{username}` (served from the cache the scrape just wrote).

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_api_stream.py -v`
Expected: PASS (`test_stream_emits_progress_then_done`).

- [ ] **Step 5: Run the whole suite**

Run: `pytest -v`
Expected: ALL tests pass across all files.

- [ ] **Step 6: Manual smoke test (optional but recommended)**

Run (from `backend/`): `uvicorn app.main:app --reload --port 8001`
Then in another shell: `curl http://localhost:8001/api/health` → `{"status":"ok"}`.
With a real public PSN id: `curl http://localhost:8001/api/profile/<psn_id>` → JSON profile (first call scrapes; may take a while).

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/profile.py backend/tests/test_api_stream.py
git commit -m "feat(backend): add SSE scrape-progress stream endpoint"
```

---

## Self-Review (against the spec)

**Spec coverage (Phase 1 scope + backend sections §4):**
- §4.1 module structure → Tasks 1–7 create `app/{main,config,models}`, `app/api/{meta,profile}`, `app/services/{http,psnprofiles,profile_service}`, `app/core/cache`. ✅ (`services/{hltb,guide,psn_playtime,metacritic,exophase,links,matching}` are Phase 3/4 — intentionally deferred.)
- §4.2 endpoints → `/health` (Task 1), `/profile/{username}` + `?refresh` (Task 6), `/profile/{username}/stream` SSE (Task 7). `/api/me` is Phase 4; `/refresh` is folded into the `refresh` query param. ✅
- §4.3 models → `Trophy`, `ProfileSummary`, `TrophyCounts`, `ProfileData` (Task 2). `GameSummary`/`Enrichment` are Phase 3. ✅
- §4.4 caching → `FileCache` with per-load TTL; profile at 24h (Tasks 5–6); namespaced keys leave room for enrichment TTLs later. ✅
- §8 error handling → 404 for missing/private, 502 on upstream error, malformed rows skipped, empty pages end pagination. ✅
- §9 testing → pytest with HTML fixtures for parsers, FakeSession for scraping, tmp_path for cache, TestClient for API + SSE. ✅

**Placeholder scan:** No TBD/TODO; every code step shows complete code; every run step shows the exact command + expected result. ✅

**Type consistency:** `on_progress` is `(page)` inside `fetch_trophy_log` and `(page, total)` at `scrape_profile`/`get_profile`/stream — consistent across Tasks 4/6/7. `ProfileData.model_dump()`/`model_validate()` used consistently for cache + API. `FileCache._path` used by both `cache.py` and its test. ✅

---

## Next Phases (separate plans, written when reached)

- **Phase 2 — Frontend foundation:** Vite + React + TS + Tailwind + shadcn/ui, Trophy Gold theme, top-nav routing, Overview/Timeline/Milestones/Data pages (Recharts), wired to this backend (incl. consuming the SSE stream).
- **Phase 3 — Enrichment:** `hltb`, `guide`, `metacritic`, `exophase`, `links`, `matching` services + `GameSummary`/`Enrichment` models + `/profile/{username}/games` + Games page & GameCard with external links. (Starts with a short library/endpoint validation spike.)
- **Phase 4 — PSN real playtime:** PSNAWP + NPSSO, `/api/me`, own-profile reconciliation.
- **Phase 5 — Polish & deploy-readiness:** remove the old Streamlit app, README, run scripts, remaining tests.
