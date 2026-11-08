from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from app.config import settings
from app.core.cache import FileCache
from app.services.trophy_images import (
    ImageUnavailableError,
    get_official_image,
    is_official_trophy_image,
)

router = APIRouter()


@router.get("/images/official")
def read_official_image(url: str = Query(..., min_length=1, max_length=2048)):
    if not is_official_trophy_image(url):
        raise HTTPException(status_code=400, detail="Unsupported trophy image URL.")
    try:
        path, media_type = get_official_image(url, FileCache(settings.cache_dir))
    except ImageUnavailableError:
        raise HTTPException(
            status_code=503, detail="Trophy artwork is temporarily unavailable.",
            headers={"Cache-Control": "no-store", "Retry-After": "60"},
        ) from None
    return FileResponse(
        path, media_type=media_type,
        headers={"Cache-Control": "public, max-age=31536000, immutable",
                 "X-Content-Type-Options": "nosniff"},
    )
