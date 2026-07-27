import functools
from typing import Callable

from app.config import settings
from app.core.cache import FileCache
from app.models import ProfileData
from app.services import psnprofiles
from app.services.http import create_session
from app.services.psn_service import build_profile_from_psn, psn_online_id

PROFILE_TTL = 86400  # 24 hours


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
    key = f"profile/{username.lower()}"

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
