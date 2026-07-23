import requests
from fastapi import APIRouter, HTTPException, Query

from app.services.profile_service import get_profile

router = APIRouter()


@router.get("/profile/{username}")
def read_profile(username: str, refresh: bool = Query(False)):
    try:
        data = get_profile(username, force=refresh)
    except requests.exceptions.RequestException:
        raise HTTPException(status_code=502, detail="Error fetching profile from PSNProfiles.")
    if data is None:
        raise HTTPException(status_code=404, detail=f"Profile '{username}' not found or is private.")
    return data.model_dump()
