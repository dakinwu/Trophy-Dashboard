"""On-demand PSNProfiles profile statistics for official-API profiles."""

from __future__ import annotations

import hashlib
import re
from urllib.parse import quote

from app.config import settings
from app.core.cache import FileCache
from app.services.http import create_session
from app.services.psnprofiles import PSN_BASE, fetch_summary

_PROFILE_STATS_TTL = 6 * 3600


def _rank_number(value: str | None) -> int | None:
    if not value:
        return None
    digits = re.sub(r"[^\d]", "", value)
    return int(digits) if digits else None


def extract_psnprofiles_stats(
    stats: dict[str, str],
    profile_url: str,
) -> dict[str, int | str | None]:
    """Extract rank fields without assuming a fixed country-label wording."""
    world_rank: int | None = None
    country_rank: int | None = None
    country_label: str | None = None

    for label, value in stats.items():
        normalised_label = " ".join(label.casefold().split())
        if normalised_label == "world rank":
            world_rank = _rank_number(value)
        elif normalised_label == "country rank" or (
            normalised_label.endswith(" rank")
            and normalised_label not in {"world rank", "level rank"}
        ):
            country_rank = _rank_number(value)
            country_label = label

    return {
        "world_rank": world_rank,
        "country_rank": country_rank,
        "country_label": country_label,
        "completion": stats.get("Completion"),
        "profile_url": profile_url,
    }


def get_psnprofiles_stats(
    username: str,
    *,
    cache: FileCache | None = None,
    session=None,
) -> dict[str, int | str | None] | None:
    """Fetch and short-cache PSNProfiles ranks for one public profile."""
    username = (username or "").strip()
    if not username:
        return None

    cache = cache or FileCache(settings.cache_dir)
    digest = hashlib.sha256(username.casefold().encode("utf-8")).hexdigest()
    key = f"psnprofiles_stats/{digest}"
    cached = cache.load(key, _PROFILE_STATS_TTL)
    if cached is not None:
        return cached or None

    profile_url = f"{PSN_BASE}/{quote(username, safe='')}"
    owns_session = session is None
    session = session or create_session()
    try:
        summary = fetch_summary(session, profile_url)
        if summary is None:
            return None
        result = extract_psnprofiles_stats(summary.stats, profile_url)
        cache.save(key, result)
        return result
    finally:
        if owns_session:
            session.close()
