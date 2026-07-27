"""HowLongToBeat enrichment — average completion times per game.

Times are game-level (not per-user), so they're cached with a long TTL and
shared across profiles. HLTB lookups are serialized with a small politeness
delay so that many game cards requesting at once don't trip HLTB's own rate
limiting.
"""
from __future__ import annotations

import inspect
import logging
import threading
import time

from app.config import settings
from app.core.cache import FileCache

logger = logging.getLogger(__name__)

_HLTB_TTL = 30 * 24 * 3600  # times barely change
_lock = threading.Lock()
_last_call = 0.0
_MIN_INTERVAL = 0.4  # seconds between outbound HLTB requests


def get_hltb_times(game: str, cache: FileCache | None = None) -> dict | None:
    """{game_name, main_story, main_extra, completionist} (hours) for `game`,
    or None if not found. A cached empty dict means 'looked up, no match'."""
    game = (game or "").strip()
    if not game:
        return None
    cache = cache or FileCache(settings.cache_dir)
    key = f"hltb/{game.lower()}"

    cached = cache.load(key, _HLTB_TTL)
    if cached is not None:
        return cached or None

    result = _search(game)
    cache.save(key, result or {})
    return result


def _search(game: str) -> dict | None:
    global _last_call
    with _lock:
        wait = _MIN_INTERVAL - (time.monotonic() - _last_call)
        if wait > 0:
            time.sleep(wait)
        _last_call = time.monotonic()
    try:
        from howlongtobeatpy import HowLongToBeat

        results = HowLongToBeat().search(game)
        if inspect.iscoroutine(results):
            import asyncio

            results = asyncio.new_event_loop().run_until_complete(results)
        if not results:
            return None
        best = max(results, key=lambda e: e.similarity)
        return {
            "game_name": best.game_name,
            "main_story": best.main_story,
            "main_extra": best.main_extra,
            "completionist": best.completionist,
        }
    except Exception as e:
        logger.warning("HLTB lookup failed for %r: %s", game, e)
        return None
