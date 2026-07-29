import functools
import hashlib
import logging
import re
from typing import Callable

from app.config import settings
from app.core.cache import FileCache
from app.models import GameTrophyDetail, ProfileData
from app.services import psnprofiles
from app.services.http import create_session
from app.services.psn_service import (
    build_game_detail_from_psn,
    build_profile_from_psn,
    psn_online_id,
)

PROFILE_TTL = 86400  # 24 hours
GAME_DETAIL_TTL = 6 * 3600
logger = logging.getLogger(__name__)


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
    # v4 invalidates profiles built before trophies carried DLC metadata.
    key = f"profile_v4/{username.lower()}"

    if not force:
        cached = cache.load(key, PROFILE_TTL)
        if cached is not None:
            return ProfileData.model_validate(cached)

    # Hybrid source selection: the token owner's OWN profile comes from the
    # official PSN API (no Cloudflare); everyone else uses the PSNProfiles
    # scraper. An injected `session` (tests) forces the scraper path.
    if session is None and settings.psn_npsso:
        owner = _token_owner_online_id()
        if owner and owner.lower() == username.lower():
            data = build_profile_from_psn(
                cache=cache, on_progress=on_progress, should_stop=should_stop
            )
            if data is not None:
                cache.save(key, data.model_dump())
                return data

    owns_session = session is None
    session = session or create_session()
    try:
        data = psnprofiles.scrape_profile(
            session, username, on_progress=on_progress, should_stop=should_stop
        )
    finally:
        if owns_session:
            session.close()
    if data is None:
        return None

    cache.save(key, data.model_dump())
    return data


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
    detail_key = f"game_detail_v1/{detail_digest}"
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
