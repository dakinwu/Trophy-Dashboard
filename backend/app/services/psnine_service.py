"""Resolve PSN trophy-list names to PSNine's Simplified Chinese game names."""

from __future__ import annotations

import hashlib
import logging
import re
import threading
import time
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

from app.config import settings
from app.core.cache import FileCache

logger = logging.getLogger(__name__)

PSNINE_SEARCH_URL = "https://www.psnine.com/psngame"
_PSNINE_TITLE_TTL = 180 * 24 * 3600
_MIN_INTERVAL = 0.5
_lock = threading.Lock()
_last_call = 0.0
_PSNGAME_PATH = re.compile(r"^/psngame/\d+/?$")
_HAN_CHARACTER = re.compile(r"[\u3400-\u9fff]")


def build_psnine_url(simplified_chinese_title: str) -> str:
    return f"{PSNINE_SEARCH_URL}?title={quote(simplified_chinese_title, safe='')}"


def parse_psnine_title(html: str) -> str | None:
    """Return the first Simplified Chinese result title from a PSNine search."""
    soup = BeautifulSoup(html, "html.parser")
    for anchor in soup.select('a[href*="/psngame/"]'):
        href = anchor.get("href", "")
        path = re.sub(r"^https?://(?:www\.)?psnine\.com", "", href)
        title = anchor.get_text(" ", strip=True)
        if _PSNGAME_PATH.match(path) and title and _HAN_CHARACTER.search(title):
            return title
    return None


def get_psnine_title(
    game: str,
    *,
    cache: FileCache | None = None,
    session=None,
) -> str | None:
    """Resolve and long-cache PSNine's own Simplified Chinese title for `game`."""
    game = (game or "").strip()
    if not game:
        return None

    cache = cache or FileCache(settings.cache_dir)
    digest = hashlib.sha256(game.casefold().encode("utf-8")).hexdigest()
    key = f"psnine_title/{digest}"
    cached = cache.load(key, _PSNINE_TITLE_TTL)
    if cached is not None:
        return cached.get("title") or None

    title = _search(game, session=session)
    # Do not turn a transient PSNine/network failure into a six-month miss.
    if title:
        cache.save(key, {"title": title})
    return title


def _search(game: str, session=None) -> str | None:
    global _last_call
    with _lock:
        wait = _MIN_INTERVAL - (time.monotonic() - _last_call)
        if wait > 0:
            time.sleep(wait)
        _last_call = time.monotonic()

        client = session or requests
        try:
            response = client.get(
                PSNINE_SEARCH_URL,
                params={"title": game},
                headers={"User-Agent": settings.scrape_user_agent},
                timeout=15,
            )
            response.raise_for_status()
            return parse_psnine_title(response.text)
        except requests.RequestException as exc:
            logger.warning("PSNine title lookup failed for %r: %s", game, exc)
            return None
