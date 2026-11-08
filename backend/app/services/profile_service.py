import functools
import hashlib
import json
import logging
import re
import threading
import unicodedata
from datetime import datetime, timezone
from typing import Callable

from app.config import settings
from app.core.cache import FileCache
from app.models import GameTrophyDetail, PlatinumGallery, ProfileData, Trophy
from app.services import psnprofiles
from app.services.http import create_session
from app.services.trophy_images import is_official_trophy_image
from app.services.psn_service import (
    build_game_detail_from_psn,
    build_platinum_gallery_from_psn,
    build_profile_from_psn,
    build_public_profile_summary_from_psn,
    psn_online_id,
)

PROFILE_TTL = 86400  # 24 hours
GAME_DETAIL_TTL = 6 * 3600
logger = logging.getLogger(__name__)
_GALLERY_LOCKS = [threading.Lock() for _ in range(8)]


def get_platinum_gallery(username: str, *, force: bool = False, cache=None) -> PlatinumGallery | None:
    cache = cache or FileCache(settings.cache_dir)
    key = f"psn_platinum_gallery_v1/{username.casefold()}"
    slot = int(hashlib.sha256(username.casefold().encode()).hexdigest()[:2], 16) % 8
    with _GALLERY_LOCKS[slot]:
        cached = cache.load(key, PROFILE_TTL)
        if cached is not None and not force:
            gallery = PlatinumGallery.model_validate(cached)
            gallery.cache_status = "cached"
            return gallery
        previous = cache.load(key, float("inf"))
        try:
            gallery = build_platinum_gallery_from_psn(username, cache)
        except Exception:
            if previous is None:
                raise
            gallery = None
        if gallery is not None and gallery.complete:
            cache.save(key, gallery.model_dump())
            return gallery
        if previous is not None:
            gallery = PlatinumGallery.model_validate(previous)
            gallery.cache_status = "cached"
        return gallery


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


def _earned_stamp(value: str) -> str:
    """Compare Sony ISO timestamps with PSNProfiles' English UTC log dates."""
    value = re.sub(r"(\d+)(st|nd|rd|th)\b", r"\1", value, flags=re.IGNORECASE)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = datetime.strptime(value, "%d %b %Y %I:%M:%S %p")
        except ValueError:
            return ""
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


def _icon_name(value: str) -> str:
    return _normalise_name(_game_name_without_platform(re.sub(r"[®™]", "", value)))


def _official_icon_maps(
    cache: FileCache,
) -> tuple[dict[tuple[str, str], str], dict[tuple[str, str, str], set[str]]]:
    """Artwork remains usable after statistics expire; include both Sony CDNs."""
    by_game_and_title: dict[tuple[str, str], str] = {}
    by_earned: dict[tuple[str, str, str], set[str]] = {}

    paths = []
    for pattern in ("psn_title_v2__*.json", "psn_game_detail_v2__*.json", "profile*__*.json"):
        for path in cache.base_dir.glob(pattern):
            try:
                paths.append((path.stat().st_mtime, path))
            except OSError:
                continue
    for _, path in sorted(paths, reverse=True):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(payload, dict):
            continue
        for trophy in payload.get("trophies", payload.get("trophy_log", [])):
            if not isinstance(trophy, dict):
                continue
            icon_url = str(trophy.get("icon_url") or "")
            if not is_official_trophy_image(icon_url):
                continue
            game = _icon_name(str(trophy.get("game") or ""))
            title = _icon_name(str(trophy.get("title") or ""))
            if not game or not title:
                continue
            by_game_and_title.setdefault((game, title), icon_url)
            stamp = _earned_stamp(str(trophy.get("timestamp") or ""))
            if stamp:
                earned_key = (title, str(trophy.get("grade") or ""), stamp)
                by_earned.setdefault(earned_key, set()).add(icon_url)

    return by_game_and_title, by_earned


def _replace_blocked_official_icons(
    trophies: list[Trophy],
    cache: FileCache,
) -> int:
    """Replace blocked PSNProfiles image URLs on a trophy list."""
    if not any(t.icon_url.startswith("https://img.psnprofiles.com/") for t in trophies):
        return 0
    by_game_and_title, by_earned = _official_icon_maps(cache)
    if not by_game_and_title:
        return 0

    replacements = 0
    for trophy in trophies:
        if not trophy.icon_url.startswith("https://img.psnprofiles.com/"):
            continue
        game = _icon_name(trophy.game)
        title = _icon_name(trophy.title)
        icon_url = by_game_and_title.get((game, title))
        if icon_url is None:
            # Localized game names may differ, but a trophy title alone is not
            # identity: require the exact earned timestamp and grade as well.
            candidates = by_earned.get((title, trophy.grade, _earned_stamp(trophy.timestamp)), set())
            if len(candidates) == 1:
                icon_url = next(iter(candidates))
        if icon_url is not None:
            trophy.icon_url = icon_url
            replacements += 1
    return replacements


def _with_cached_official_icons(
    profile: ProfileData,
    cache: FileCache,
) -> ProfileData:
    """Replace blocked PSNProfiles trophy images with official cached icons.

    PSNProfiles currently serves trophy images through a Cloudflare-protected
    host.  The trophy data itself is still useful, so use recent official PSN
    title caches when an exact game + trophy match is available.  This keeps
    the fallback profile usable without changing its source or rarity data.
    """
    _with_platinum_gallery(profile, cache)
    replacements = _replace_blocked_official_icons(
        profile.trophy_log + profile.platinum_trophies, cache,
    )

    if replacements:
        logger.info(
            "Replaced %d blocked PSNProfiles trophy icons with official cached icons",
            replacements,
        )
    return profile


def _with_platinum_gallery(profile: ProfileData, cache: FileCache) -> None:
    """Keep known earned platinum records if a fallback log stops partway.

    Gallery snapshots are per player. They never add earned trophies to the
    statistics/log and are replaced when a full platinum set is retrieved.
    """
    current = [t for t in profile.trophy_log if t.grade == "Platinum" and t.earned]
    expected = profile.profile_summary.total_trophies.platinum
    username = profile.profile_summary.username.casefold()
    key = f"platinum_gallery_v1/{username}"
    if profile.summary_only:
        return
    if len(current) == expected:
        profile.platinum_trophies = current
        cache.save(key, {"trophies": [t.model_dump() for t in current]})
        return
    saved_gallery = cache.load(f"psn_platinum_gallery_v1/{username}", float("inf"))
    if saved_gallery and saved_gallery.get("complete") and saved_gallery.get("total_count") == expected:
        profile.platinum_trophies = PlatinumGallery.model_validate(saved_gallery).trophies
        return

    def identity(trophy: Trophy) -> tuple[str, str]:
        stamp = _earned_stamp(trophy.timestamp)
        return (_icon_name(trophy.title), stamp or f"{trophy.game}:{trophy.platforms}")

    known = {identity(t): t for t in current}
    snapshot = cache.load(key, float("inf"))
    historical = [snapshot] if snapshot else []
    # Migrate existing on-disk player profiles without treating their old
    # progress or rarity statistics as fresh.
    for version in ("profile_v4", "profile_v3", "profile"):
        candidate = cache.load(f"{version}/{username}", float("inf"))
        if not isinstance(candidate, dict):
            continue
        owner = candidate.get("profile_summary", {}).get("username", "")
        if str(owner).casefold() == username:
            historical.append({"trophies": candidate.get("trophy_log", [])})
    for payload in historical:
        for row in payload.get("trophies", []):
            if not isinstance(row, dict) or row.get("grade") != "Platinum":
                continue
            try:
                trophy = Trophy.model_validate(row)
            except ValueError:
                continue
            if trophy.earned:
                known.setdefault(identity(trophy), trophy)
    gallery = list(known.values())
    # A smaller authoritative total can mean removed/hidden trophies. Do not
    # resurrect a historical set that exceeds that total.
    if len(gallery) > expected:
        gallery = current
    gallery.sort(key=lambda trophy: _earned_stamp(trophy.timestamp), reverse=True)
    profile.platinum_trophies = gallery
    cache.save(key, {"trophies": [t.model_dump() for t in gallery]})


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
                    _with_cached_official_icons(
                        _mark_cached_profile(cached_profile, cache, key),
                        cache,
                    ),
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
                    return _with_cached_psnprofiles_rarities(
                        _with_cached_official_icons(data, cache),
                        cache,
                    )

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
    return _with_cached_psnprofiles_rarities(
        _with_cached_official_icons(data, cache),
        cache,
    )


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
        detail = GameTrophyDetail.model_validate(cached_detail)
        _replace_blocked_official_icons(detail.trophies, cache)
        return detail

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
    detail = GameTrophyDetail(
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
    _replace_blocked_official_icons(detail.trophies, cache)
    return detail
