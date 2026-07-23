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
