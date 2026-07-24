"""PSN official-API data source (via PSNAWP + an NPSSO token).

Produces the same `ProfileData` shape the PSNProfiles scraper produces, but for
the token owner's OWN account and with NO Cloudflare in the way. Used as the
primary source for the user's own profile in the hybrid design; PSNProfiles
scraping remains the best-effort secondary source for other/public profiles.

Timestamps are emitted as ISO-8601 (the frontend parses both ISO and the older
PSNProfiles "6th Jul 2024 ..." format).
"""
from __future__ import annotations

import logging
from typing import Callable

from app.config import settings
from app.models import ProfileData, ProfileSummary, Trophy, TrophyCounts

logger = logging.getLogger(__name__)

_GRADE_NAMES = {"PLATINUM": "Platinum", "GOLD": "Gold", "SILVER": "Silver", "BRONZE": "Bronze"}
_GRADE_KEYS = ("platinum", "gold", "silver", "bronze")


def _grade_name(trophy_type) -> str:
    raw = getattr(trophy_type, "name", str(trophy_type)).upper()
    return _GRADE_NAMES.get(raw, raw.title())


def _client(npsso: str):
    from psnawp_api import PSNAWP

    return PSNAWP(npsso).me()


def psn_online_id(npsso: str | None = None) -> str | None:
    """Return the token owner's PSN online id, or None if no/invalid token."""
    npsso = npsso or settings.psn_npsso
    if not npsso:
        return None
    try:
        return _client(npsso).online_id
    except Exception as e:  # invalid/expired token, network, etc.
        logger.warning("PSN online_id lookup failed: %s", e)
        return None


def _format_playtime(total_seconds: float) -> str:
    return f"{int(total_seconds // 3600):,}h"


def build_profile_from_psn(
    npsso: str | None = None,
    *,
    on_progress: Callable[[int, int], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
    max_titles: int | None = None,
) -> ProfileData | None:
    """Build ProfileData for the token owner's own account from the PSN API.

    Returns None if no token is configured.
    """
    npsso = npsso or settings.psn_npsso
    if not npsso:
        return None

    me = _client(npsso)
    online_id = me.online_id

    stats: dict[str, str] = {}
    avatar_url: str | None = None

    # Best-effort level + avatar — never fail the whole profile over these.
    try:
        summary = me.trophy_summary()
        level = getattr(summary, "trophy_level", None)
        if level is not None:
            stats["Level"] = str(level)
    except Exception as e:
        logger.info("trophy_summary unavailable: %s", e)
    try:
        prof = me.get_profile_legacy()
        avatars = ((prof or {}).get("profile", {}) or {}).get("avatarUrls") or []
        if avatars and isinstance(avatars[0], dict):
            avatar_url = avatars[0].get("avatarUrl")
    except Exception as e:
        logger.info("avatar lookup unavailable: %s", e)

    # Per-game real playtime (seconds), keyed by title name (best-effort).
    playtime_seconds: dict[str, float] = {}
    try:
        for s in me.title_stats():
            dur = getattr(s, "play_duration", None)
            if dur is not None:
                playtime_seconds[s.name] = dur.total_seconds()
    except Exception as e:
        logger.info("title_stats unavailable: %s", e)

    titles = list(me.trophy_titles())
    if max_titles is not None:
        titles = titles[:max_titles]
    total_titles = len(titles)

    counts = TrophyCounts()
    log: list[Trophy] = []
    errors = 0

    for idx, title in enumerate(titles):
        if should_stop is not None and should_stop():
            break
        try:
            platform = next(iter(title.title_platform))
            trophies = me.trophies(
                np_communication_id=title.np_communication_id,
                platform=platform,
                include_progress=True,
            )
            for tr in trophies:
                if not getattr(tr, "earned", False):
                    continue
                grade = _grade_name(getattr(tr, "trophy_type", ""))
                key = grade.lower()
                if key in _GRADE_KEYS:
                    setattr(counts, key, getattr(counts, key) + 1)
                earned_dt = getattr(tr, "earned_date_time", None)
                rate = getattr(tr, "trophy_earn_rate", None)
                log.append(
                    Trophy(
                        game=title.title_name,
                        icon_url=getattr(tr, "trophy_icon_url", "") or "",
                        title=getattr(tr, "trophy_name", "") or "",
                        timestamp=earned_dt.isoformat() if earned_dt else "",
                        rarity_percent=f"{rate}%" if rate is not None else "N/A",
                        grade=grade,
                    )
                )
        except Exception as e:
            errors += 1
            logger.warning("Skipping title %r: %s", getattr(title, "title_name", "?"), e)
        if on_progress is not None:
            on_progress(idx + 1, total_titles)

    counts.total = counts.platinum + counts.gold + counts.silver + counts.bronze

    # A real profile with titles always has earned trophies; zero means every
    # per-title fetch failed (typically PSN rate-limiting). Treat as a failed
    # fetch and return None so the caller does NOT cache this garbage.
    if titles and not log:
        logger.warning(
            "PSN fetch for %s yielded 0 trophies from %d titles (%d errored); "
            "treating as throttled/failed, not caching.",
            online_id, len(titles), errors,
        )
        return None

    if playtime_seconds:
        stats["Playtime"] = _format_playtime(sum(playtime_seconds.values()))
    stats["Source"] = "PSN API"

    return ProfileData(
        profile_summary=ProfileSummary(
            username=online_id,
            avatar_url=avatar_url,
            total_trophies=counts,
            stats=stats,
        ),
        trophy_log=log,
        game_playtime_seconds={name: int(sec) for name, sec in playtime_seconds.items()},
    )
