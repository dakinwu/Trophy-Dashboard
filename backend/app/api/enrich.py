from fastapi import APIRouter, Query

from app.services.hltb_service import get_hltb_times

router = APIRouter()


@router.get("/hltb")
def hltb(game: str = Query(..., min_length=1)):
    """HowLongToBeat completion times for a game. Returns {} if not found."""
    return get_hltb_times(game) or {}
