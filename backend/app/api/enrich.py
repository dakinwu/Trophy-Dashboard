from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse

from app.services.hltb_service import get_hltb_times
from app.services.http import PSNProfilesFetchError
from app.services.psnine_service import (
    build_psnine_url,
    get_psnine_title,
)
from app.services.psnprofiles_guide_service import get_psnprofiles_guide
from app.services.psnprofiles_stats_service import get_psnprofiles_stats
from app.services.psnprofiles_trophies_service import get_psnprofiles_trophies

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


@router.get("/psnprofiles/trophies")
def psnprofiles_trophies(
    game: str = Query(..., min_length=1),
    platform: str | None = Query(None),
):
    """On-demand per-trophy rarity percentages for one title/platform."""
    try:
        return get_psnprofiles_trophies(game, platform) or {}
    except PSNProfilesFetchError as exc:
        raise HTTPException(
            status_code=502,
            detail="Error fetching PSNProfiles trophy rarity data.",
        ) from exc


@router.get("/psnine")
def psnine(game: str = Query(..., min_length=1)):
    """Resolve a title and redirect to a non-empty PSNine title search."""
    title = get_psnine_title(game) or game.strip()
    return RedirectResponse(
        build_psnine_url(title),
        status_code=307,
    )
