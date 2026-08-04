import functools
import hashlib
import json
import logging
import re
import unicodedata
from datetime import datetime, timezone
from typing import Callable

from app.config import settings
from app.core.cache import FileCache
from app.models import GameTrophyDetail, ProfileData
from app.services import psnprofiles
from app.services.http import create_session
from app.services.psn_service import (
    build_game_detail_from_psn,
    build_profile_from_psn,
    build_public_profile_summary_from_psn,
    psn_online_id,
)

PROFILE_TTL = 86400  # 24 hours
GAME_DETAIL_TTL = 6 * 3600
logger = logging.getLogger(__name__)


def _legacy_profile_source(profile: ProfileData) -> str | None:
    source_label = profile.profile_summary.stats.get("Source", "").casefold()
    if "psn api" in source_label:
        return "psn"
    if "psnprofiles" in source_label:
        return "psnprofiles"
    if any(trophy.rarity_source == "psn" for trophy in profile.trophy_log):
        return "psn"
    if any(trophy.rarity_source == "psnprofiles" for trophy in profile.trophy_log):
        return "psnprofiles"
    return None


def _mark_live_profile(profile: ProfileData, source: str) -> ProfileData:
    profile.profile_source = source
    profile.cache_status = "live"
    profile.fetched_at = datetime.now(timezone.utc).isoformat()
    return profile


def _mark_cached_profile(
    profile: ProfileData,
    cache: FileCache,
    key: str,
) -> ProfileData:
    profile.profile_source = profile.profile_source or _legacy_profile_source(profile)
    profile.cache_status = "cached"
    if not profile.fetched_at:
        modified_at = cache.modified_at(key)
        if modified_at is not None:
            profile.fetched_at = datetime.fromtimestamp(
                modified_at,
                tz=timezone.utc,
            ).isoformat()
    return profile


def _normalise_name(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"[\W_]+", " ", value, flags=re.UNICODE).strip()


def _game_name_without_platform(value: str) -> str:
    return re.sub(
        r"\s+\((?:PS3|PS4|PS5|PS\s*VITA|PSVITA|PSPC)\)\s*$",
        "",
        value,
        flags=re.IGNORECASE,
    )


def _percent_value(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(value.rstrip("%").strip())
    except ValueError:
        return None


def _tracked_rarity(
    cached_trophy: dict,
    official_rarity: str | None,
) -> str | None:
    """Choose the tracked-player value from a cached dual-rarity row."""
    official = _percent_value(official_rarity)
    candidates = cached_trophy.get("rarity_percentages") or []
    if official is not None:
        for candidate in candidates:
            parsed = _percent_value(candidate)
            if parsed is not None and abs(parsed - official) > 0.0001:
                return candidate
        return None
    return cached_trophy.get("psnprofiles_rarity_percent")


def _with_cached_psnprofiles_rarities(
    profile: ProfileData,
    cache: FileCache,
) -> ProfileData:
    """Add PSNProfiles rates already fetched by game-detail pages.

    This is deliberately cache-only: loading the overview must never open a
    browser or crawl every game in a large account.
    """
    cached_lists: list[dict] = []
    for path in cache.base_dir.glob("psnprofiles_trophies_v6__*.json"):
        try:
            cached_lists.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            continue

    if not cached_lists:
        return profile

    by_game: dict[tuple[str, str], dict[tuple[str, int | None], dict]] = {}
    for cached in cached_lists:
        game_name = _normalise_name(cached.get("title", ""))
        platforms = {
            value.strip().upper()
            for value in cached.get("platform", "").split(",")
            if value.strip()
        } or {"UNKNOWN"}
        trophy_map: dict[tuple[str, int | None], dict] = {}
        for trophy in cached.get("trophies", []):
            trophy_key = (
                _normalise_name(trophy.get("title", "")),
                trophy.get("trophy_id"),
            )
            trophy_map[trophy_key] = trophy
        for platform in platforms:
            by_game[(game_name, platform)] = trophy_map

    for trophy in profile.trophy_log:
        if trophy.psnprofiles_rarity_percent:
            continue
        game_name = _normalise_name(_game_name_without_platform(trophy.game))
        trophy_name = _normalise_name(trophy.title)
        for platform in trophy.platforms:
            trophy_map = by_game.get((game_name, platform))
            if trophy_map is None:
                continue
            cached_trophy = trophy_map.get((trophy_name, trophy.trophy_id))
            if cached_trophy is None:
                cached_trophy = next(
                    (
                        value
                        for (title, _trophy_id), value in trophy_map.items()
                        if title == trophy_name
                    ),
                    None,
                )
            if cached_trophy is not None:
                trophy.psnprofiles_rarity_percent = _tracked_rarity(
                    cached_trophy,
                    trophy.psn_rarity_percent,
                )
                break
    return profile


@functools.lru_cache(maxsize=1)
def _token_owner_online_id() -> str | None:
    """The NPSSO token owner's PSN online id (cached per process); None if unset."""
    return psn_online_id()


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
    # Keep the profile cache stable; DLC metadata is fetched with the complete
    # per-game detail endpoint below and does not require rebuilding the whole
    # account profile.
    key = f"profile_v3/{username.lower()}"

    if not force:
        cached = cache.load(key, PROFILE_TTL)
        if cached is not None:
            cached_profile = ProfileData.model_validate(cached)
            # A positive trophy total with no rows is a failed log scrape,
            # rather than a valid empty account.
            if not (
                cached_profile.profile_summary.total_trophies.total > 0
                and not cached_profile.trophy_log
                and not cached_profile.summary_only
            ):
                return _with_cached_psnprofiles_rarities(
                    _mark_cached_profile(cached_profile, cache, key),
                    cache,
                )

    # Prefer Sony's API for the token owner and other public accounts. This
    # avoids the PSNProfiles trophy-log page, which can stall behind ads or
    # Cloudflare. An injected `session` (tests) forces the scraper path.
    if session is None and settings.psn_npsso:
        owner = _token_owner_online_id()
        if owner:
            try:
                if owner.casefold() == username.casefold():
                    data = build_profile_from_psn(
                        cache=cache,
                        on_progress=on_progress,
                        should_stop=should_stop,
                    )
                else:
                    data = build_public_profile_summary_from_psn(username)
            except Exception as exc:
                logger.warning("Official profile lookup failed: %s", exc)
            else:
                if data is not None:
                    _mark_live_profile(data, "psn")
                    cache.save(key, data.model_dump())
                    return _with_cached_psnprofiles_rarities(data, cache)

    owns_session = session is None
    session = session or create_session()
    try:
        data = psnprofiles.scrape_profile(
            session, username, on_progress=on_progress, should_stop=should_stop
        )
    finally:
        if owns_session:
            session.close()
    if data is None or (
        data.profile_summary.total_trophies.total > 0
        and not data.trophy_log
        and not data.summary_only
    ):
        logger.warning(
            "Profile lookup for %s returned a summary without trophy rows; "
            "not caching the incomplete response.",
            username,
        )
        return None

    _mark_live_profile(data, "psnprofiles")
    cache.save(key, data.model_dump())
    return _with_cached_psnprofiles_rarities(data, cache)


def get_game_detail(
    username: str,
    game: str,
    *,
    cache: FileCache | None = None,
) -> GameTrophyDetail | None:
    """Return one game's trophies without changing the profile-log contract."""
    game = (game or "").strip()
    if not game:
        return None
    cache = cache or FileCache(settings.cache_dir)
    detail_digest = hashlib.sha256(
        f"{username.casefold()}:{game.casefold()}".encode("utf-8")
    ).hexdigest()
    # v2 includes the official trophy-group metadata used to label DLC rows.
    detail_key = f"game_detail_v2/{detail_digest}"
    cached_detail = cache.load(detail_key, GAME_DETAIL_TTL)
    if cached_detail is not None:
        return GameTrophyDetail.model_validate(cached_detail)

    if settings.psn_npsso:
        owner = _token_owner_online_id()
        if owner and owner.lower() == username.lower():
            try:
                detail = build_game_detail_from_psn(game, cache=cache)
            except Exception as exc:
                logger.warning("Official game-detail lookup failed: %s", exc)
            else:
                if detail is not None:
                    cache.save(detail_key, detail.model_dump())
                    return detail

    profile = get_profile(username, cache=cache)
    if profile is None:
        return None
    trophies = [
        trophy for trophy in profile.trophy_log if trophy.game.casefold() == game.casefold()
    ]
    if not trophies:
        return None

    platforms = sorted(
        {platform for trophy in trophies for platform in trophy.platforms},
        key=lambda platform: {
            "PS5": 0,
            "PS4": 1,
            "PS3": 2,
            "PSVITA": 3,
            "PSPC": 4,
            "UNKNOWN": 5,
        }[platform],
    )
    return GameTrophyDetail(
        game=game,
        display_name=re.sub(
            r"\s+\((?:PS3|PS4|PS5|PS\s*VITA|PSVITA|PSPC)\)\s*$",
            "",
            game,
            flags=re.IGNORECASE,
        ),
        platforms=platforms or ["UNKNOWN"],
        trophies=trophies,
        complete=False,
        source="profile_log",
    )
