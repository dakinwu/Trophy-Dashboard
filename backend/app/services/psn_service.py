"""PSN official-API data source (via PSNAWP + an NPSSO token).

Produces the same `ProfileData` shape the PSNProfiles scraper produces, but for
the token owner's OWN account and with NO Cloudflare in the way. Used as the
primary source for the user's own profile in the hybrid design; PSNProfiles
scraping remains the best-effort secondary source for other/public profiles.

Timestamps are emitted as ISO-8601 (the frontend parses both ISO and the older
PSNProfiles "6th Jul 2024 ..." format).
"""
from __future__ import annotations

import hashlib
import logging
import re
import unicodedata
from difflib import SequenceMatcher
from typing import Callable, TypedDict

from app.config import settings
from app.models import (
    GameTrophyDetail,
    ProfileData,
    ProfileSummary,
    Trophy,
    TrophyCounts,
)

logger = logging.getLogger(__name__)

_GRADE_NAMES = {"PLATINUM": "Platinum", "GOLD": "Gold", "SILVER": "Silver", "BRONZE": "Bronze"}
_GRADE_KEYS = ("platinum", "gold", "silver", "bronze")
_TITLE_STATS_TTL = 6 * 3600
_ROMAN_NUMERAL = re.compile(r"^(?:x{0,3})(?:ix|iv|v?i{0,3})$")


class _PlaytimeEntry(TypedDict):
    name: str
    seconds: int
    platform: str | None
    title_id: str | None


def _grade_name(trophy_type) -> str:
    raw = getattr(trophy_type, "name", str(trophy_type)).upper()
    return _GRADE_NAMES.get(raw, raw.title())


def _rarity_label(trophy_rarity, earn_rate) -> str | None:
    raw = str(
        getattr(trophy_rarity, "name", None)
        or getattr(trophy_rarity, "value", None)
        or trophy_rarity
        or ""
    )
    normalised = re.sub(r"[_\s]+", " ", raw).strip().title()
    if normalised in {"Ultra Rare", "Very Rare", "Rare", "Uncommon", "Common"}:
        return normalised

    try:
        rate = float(earn_rate)
    except (TypeError, ValueError):
        return None
    if rate <= 5:
        return "Ultra Rare"
    if rate <= 10:
        return "Very Rare"
    if rate <= 20:
        return "Rare"
    if rate <= 50:
        return "Uncommon"
    return "Common"


def _optional_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _is_dlc_trophy(trophy) -> bool:
    """Return whether a PSN trophy belongs to an additional trophy group."""
    group_id = str(getattr(trophy, "trophy_group_id", "") or "").strip().lower()
    return bool(group_id and group_id not in {"default", "base", "0"})


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


def _normalise_game_name(name: str) -> str:
    name = unicodedata.normalize("NFKC", name).casefold()
    name = re.sub(r"[™®©]", "", name)
    name = re.sub(
        r"\((?:ps[345]|playstation\s*[345]|vita|cross[- ]?buy)\)",
        " ",
        name,
    )
    name = name.replace("&", " and ")
    name = re.sub(r"[^\w]+", " ", name, flags=re.UNICODE)
    return " ".join(name.split())


def _number_tokens(name: str) -> set[str]:
    return {
        token
        for token in _normalise_game_name(name).split()
        if token.isdigit() or _ROMAN_NUMERAL.fullmatch(token)
    }


def _game_name_score(left: str, right: str) -> float:
    left_normalised = _normalise_game_name(left)
    right_normalised = _normalise_game_name(right)
    if not left_normalised or not right_normalised:
        return 0.0
    if left_normalised == right_normalised:
        return 1.0

    left_numbers = _number_tokens(left)
    right_numbers = _number_tokens(right)
    if left_numbers and right_numbers and left_numbers != right_numbers:
        return 0.0

    if min(len(left_normalised), len(right_normalised)) >= 5 and (
        left_normalised in right_normalised or right_normalised in left_normalised
    ):
        return 0.92
    return SequenceMatcher(None, left_normalised, right_normalised).ratio()


def _stats_platform(stat) -> str | None:
    category = getattr(stat, "category", None)
    raw_category = str(getattr(category, "value", category) or "").casefold()
    if raw_category == "ps5_native_game":
        return "PS5"
    if raw_category == "ps4_game":
        return "PS4"

    title_id = str(getattr(stat, "title_id", None) or "").upper()
    if title_id.startswith("PPSA"):
        return "PS5"
    if title_id.startswith("CUSA"):
        return "PS4"
    return None


def _trophy_title_platform(title) -> str | None:
    console_platforms = set(_trophy_title_platforms(title)).intersection(
        {"PS3", "PS4", "PS5"}
    )
    if len(console_platforms) == 1:
        return next(iter(console_platforms))
    return None


def _trophy_title_platforms(title) -> list[str]:
    platforms = {
        str(getattr(platform, "value", platform)).upper()
        for platform in getattr(title, "title_platform", [])
    }
    supported = {"PS3", "PS4", "PS5", "PSVITA", "PSPC"}
    order = {"PS5": 0, "PS4": 1, "PS3": 2, "PSVITA": 3, "PSPC": 4}
    return sorted(platforms.intersection(supported), key=order.__getitem__)


def _display_title_names(titles: list) -> list[str]:
    """Disambiguate same-name trophy lists from different console platforms."""
    grouped: dict[str, list[int]] = {}
    for index, title in enumerate(titles):
        grouped.setdefault(_normalise_game_name(title.title_name), []).append(index)

    names = [title.title_name for title in titles]
    for indexes in grouped.values():
        platforms = {_trophy_title_platform(titles[index]) for index in indexes}
        platforms.discard(None)
        if len(platforms) < 2:
            continue
        for index in indexes:
            platform = _trophy_title_platform(titles[index])
            if platform and not re.search(
                rf"\({re.escape(platform)}\)\s*$",
                names[index],
                flags=re.IGNORECASE,
            ):
                names[index] = f"{names[index]} ({platform})"
    return names


def _match_playtime_titles(
    playtime_entries: list[_PlaytimeEntry],
    trophy_titles: list[tuple[str, str | None]],
) -> dict[str, int]:
    """Key title-stats playtime by trophy-list names and console platform."""
    matched: dict[str, int] = {}

    for trophy_title, trophy_platform in trophy_titles:
        candidates = playtime_entries
        if trophy_platform:
            same_platform = [
                entry
                for entry in candidates
                if entry["platform"] == trophy_platform
            ]
            unknown_platform = [
                entry
                for entry in candidates
                if entry["platform"] is None
            ]
            candidates = same_platform or unknown_platform

        ranked = sorted(
            (
                (_game_name_score(trophy_title, entry["name"]), entry)
                for entry in candidates
            ),
            key=lambda candidate: candidate[0],
            reverse=True,
        )
        if not ranked:
            continue
        best_score, best_entry = ranked[0]
        runner_up = ranked[1][0] if len(ranked) > 1 else 0.0
        if best_score >= 0.78 and (
            best_score >= 0.99 or best_score - runner_up >= 0.08
        ):
            matched[trophy_title] = best_entry["seconds"]

    return matched


def _title_stats_cache_key(online_id: str) -> str:
    digest = hashlib.sha256(online_id.casefold().encode("utf-8")).hexdigest()
    return f"psn_title_stats_v2/{digest}"


def _playtime_from_title_stats(
    me,
    online_id: str,
    cache,
) -> list[_PlaytimeEntry]:
    """Fetch title stats once per short TTL without collapsing cross-gen titles."""
    key = _title_stats_cache_key(online_id)
    if cache is not None:
        cached = cache.load(key, _TITLE_STATS_TTL)
        if cached is not None:
            return [
                {
                    "name": str(entry["name"]),
                    "seconds": int(entry["seconds"]),
                    "platform": entry.get("platform"),
                    "title_id": entry.get("title_id"),
                }
                for entry in cached.get("entries", [])
            ]

    entries: list[_PlaytimeEntry] = []
    try:
        for stat in me.title_stats():
            duration = getattr(stat, "play_duration", None)
            name = getattr(stat, "name", None)
            if duration is not None and name:
                entries.append(
                    {
                        "name": name,
                        "seconds": int(duration.total_seconds()),
                        "platform": _stats_platform(stat),
                        "title_id": getattr(stat, "title_id", None),
                    }
                )
    except Exception as exc:
        logger.info("title_stats unavailable: %s", exc)
        return []

    if cache is not None:
        cache.save(key, {"entries": entries})
    return entries


def _fetch_title_trophies(me, title):
    """Fetch a title's trophies with earned progress. Cross-gen / PC titles list
    multiple platforms (e.g. {PS5, PSPC}); try each — real consoles before the
    PS-PC platform, which has no trophy data — and use the 'all' group so DLC is
    included. Returns a list, or None if no platform returns trophies."""
    platforms = sorted(
        title.title_platform,
        key=lambda p: 1 if str(getattr(p, "value", p)) == "PSPC" else 0,
    )
    for platform in platforms:
        try:
            return list(
                me.trophies(
                    np_communication_id=title.np_communication_id,
                    platform=platform,
                    include_progress=True,
                    trophy_group_id="all",
                )
            )
        except Exception:
            continue
    return None


# A title's earned trophies only change when you play it, so cache them keyed by
# (np_communication_id, last_updated). On rebuild, an untouched game is a cache
# hit and costs zero API calls — only recently-played titles are re-fetched.
_TITLE_TROPHY_TTL = 30 * 24 * 3600


def _title_cache_key(title) -> str:
    lu = getattr(title, "last_updated_datetime", None)
    stamp = lu.isoformat() if lu is not None else "?"
    digest = hashlib.md5(f"{title.np_communication_id}:{stamp}".encode()).hexdigest()
    return f"psn_title_v2/{digest}"


def _earned_trophies_for_title(me, title, cache) -> list[dict] | None:
    """Earned-trophy dicts for one title, cached per (title, last_updated).
    Returns None if the title's trophies couldn't be fetched at all."""
    key = _title_cache_key(title) if cache is not None else None
    if key is not None:
        cached = cache.load(key, _TITLE_TROPHY_TTL)
        if cached is not None:
            return cached.get("trophies", [])

    trophies = _fetch_title_trophies(me, title)
    if trophies is None:
        return None

    earned: list[dict] = []
    for tr in trophies:
        if not getattr(tr, "earned", False):
            continue
        earned_dt = getattr(tr, "earned_date_time", None)
        rate = getattr(tr, "trophy_earn_rate", None)
        earned.append(
            {
                "game": title.title_name,
                "icon_url": getattr(tr, "trophy_icon_url", "") or "",
                "title": getattr(tr, "trophy_name", "") or "",
                "timestamp": earned_dt.isoformat() if earned_dt else "",
                "rarity_percent": f"{rate}%" if rate is not None else "N/A",
                "rarity_source": "psn",
                "psn_rarity_percent": (
                    f"{rate}%" if rate is not None else None
                ),
                "grade": _grade_name(getattr(tr, "trophy_type", "")),
                "trophy_id": _optional_int(getattr(tr, "trophy_id", None)),
                "is_dlc": _is_dlc_trophy(tr),
            }
        )
    if key is not None:
        cache.save(key, {"trophies": earned})
    return earned


def build_game_detail_from_psn(
    game: str,
    npsso: str | None = None,
    *,
    cache=None,
) -> GameTrophyDetail | None:
    """Fetch one complete trophy list for the token owner's account.

    Unlike the profile log, this keeps unearned trophies so the game detail
    page can mirror the console/app trophy view without changing dashboard
    totals elsewhere.
    """
    game = (game or "").strip()
    npsso = npsso or settings.psn_npsso
    if not game or not npsso:
        return None

    me = _client(npsso)
    titles = list(me.trophy_titles())
    display_names = _display_title_names(titles)
    wanted = game.casefold()
    match = next(
        (
            (title, display_name)
            for title, display_name in zip(titles, display_names, strict=True)
            if display_name.casefold() == wanted
        ),
        None,
    )
    if match is None:
        return None

    title, display_name = match
    owner = str(getattr(me, "online_id", "") or "").casefold()
    title_cache_key = _title_cache_key(title)
    detail_digest = hashlib.md5(
        f"{owner}:{title_cache_key}".encode(),
    ).hexdigest()
    detail_key = f"psn_game_detail_v2/{detail_digest}"
    if cache is not None:
        cached = cache.load(detail_key, _TITLE_TROPHY_TTL)
        if cached is not None:
            return GameTrophyDetail.model_validate(cached)

    raw_trophies = _fetch_title_trophies(me, title)
    if raw_trophies is None:
        return None

    platforms = _trophy_title_platforms(title) or ["UNKNOWN"]
    trophies: list[Trophy] = []
    for raw_trophy in raw_trophies:
        earned = bool(getattr(raw_trophy, "earned", False))
        earned_dt = getattr(raw_trophy, "earned_date_time", None)
        rate = getattr(raw_trophy, "trophy_earn_rate", None)
        percent = f"{rate}%" if rate is not None else "N/A"
        trophies.append(
            Trophy(
                game=display_name,
                platforms=platforms,
                icon_url=getattr(raw_trophy, "trophy_icon_url", "") or "",
                title=getattr(raw_trophy, "trophy_name", "") or "",
                description=getattr(raw_trophy, "trophy_detail", None),
                timestamp=earned_dt.isoformat() if earned and earned_dt else "",
                earned=earned,
                rarity_percent=percent,
                rarity_source="psn",
                rarity_label=_rarity_label(
                    getattr(raw_trophy, "trophy_rarity", None),
                    rate,
                ),
                psn_rarity_percent=percent if rate is not None else None,
                grade=_grade_name(getattr(raw_trophy, "trophy_type", "")),
                trophy_id=_optional_int(getattr(raw_trophy, "trophy_id", None)),
                is_dlc=_is_dlc_trophy(raw_trophy),
            )
        )

    detail = GameTrophyDetail(
        game=display_name,
        display_name=re.sub(
            r"\s+\((?:PS3|PS4|PS5|PS\s*VITA|PSVITA|PSPC)\)\s*$",
            "",
            display_name,
            flags=re.IGNORECASE,
        ),
        platforms=platforms,
        trophies=trophies,
        complete=True,
        source="psn",
    )
    if cache is not None:
        cache.save(detail_key, detail.model_dump())
    return detail


def build_profile_from_psn(
    npsso: str | None = None,
    *,
    cache=None,
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

    raw_playtime_seconds = _playtime_from_title_stats(me, online_id, cache)
    titles = list(me.trophy_titles())
    if max_titles is not None:
        titles = titles[:max_titles]
    total_titles = len(titles)
    display_title_names = _display_title_names(titles)
    playtime_seconds = _match_playtime_titles(
        raw_playtime_seconds,
        [
            (display_title_names[index], _trophy_title_platform(title))
            for index, title in enumerate(titles)
        ],
    )

    counts = TrophyCounts()
    log: list[Trophy] = []
    errors = 0

    for idx, title in enumerate(titles):
        if should_stop is not None and should_stop():
            break
        earned = _earned_trophies_for_title(me, title, cache)
        if earned is None:
            errors += 1
            logger.warning(
                "Skipping title %r: no platform returned trophies",
                getattr(title, "title_name", "?"),
            )
        else:
            for e in earned:
                e = {
                    **e,
                    "game": display_title_names[idx],
                    "platforms": _trophy_title_platforms(title) or ["UNKNOWN"],
                }
                key = e["grade"].lower()
                if key in _GRADE_KEYS:
                    setattr(counts, key, getattr(counts, key) + 1)
                log.append(Trophy(**e))
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

    if raw_playtime_seconds:
        stats["Playtime"] = _format_playtime(
            sum(entry["seconds"] for entry in raw_playtime_seconds)
        )
    stats["Source"] = "PSN API"

    return ProfileData(
        profile_summary=ProfileSummary(
            username=online_id,
            avatar_url=avatar_url,
            total_trophies=counts,
            stats=stats,
        ),
        trophy_log=log,
        game_playtime_seconds=playtime_seconds,
    )
