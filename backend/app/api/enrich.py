from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse

from app.services.hltb_service import get_hltb_times
from app.services.http import PSNProfilesFetchError
from app.services.psnine_service import (
    PSNINE_SEARCH_URL,
    build_psnine_url,
    get_psnine_title,
)
from app.services.psnprofiles_guide_service import get_psnprofiles_guide
from app.services.psnprofiles_stats_service import get_psnprofiles_stats

router = APIRouter()


@router.get("/hltb")
def hltb(game: str = Query(..., min_length=1)):
    """HowLongToBeat completion times for a game. Returns {} if not found."""
    return get_hltb_times(game) or {}


@router.get("/psnprofiles/guide")
def psnprofiles_guide(game: str = Query(..., min_length=1)):
    """On-demand trophy-guide difficulty, platinum time, and exact guide URL."""
    try:
        return get_psnprofiles_guide(game) or {}
    except PSNProfilesFetchError as exc:
        raise HTTPException(
            status_code=502,
            detail="Error fetching the PSNProfiles guide.",
        ) from exc


@router.get("/psnprofiles/stats")
def psnprofiles_stats(username: str = Query(..., min_length=1)):
    """On-demand PSNProfiles world/country rank for a public profile."""
    try:
        return get_psnprofiles_stats(username) or {}
    except PSNProfilesFetchError as exc:
        raise HTTPException(
            status_code=502,
            detail="Error fetching PSNProfiles rankings.",
        ) from exc


@router.get("/psnine")
def psnine(game: str = Query(..., min_length=1)):
    """Resolve a title and redirect to PSNine's Simplified Chinese search URL."""
    title = get_psnine_title(game)
    return RedirectResponse(
        build_psnine_url(title) if title else PSNINE_SEARCH_URL,
        status_code=307,
    )
