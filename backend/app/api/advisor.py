from fastapi import APIRouter, HTTPException, Query

from app.models import AdvisorBatchRequest, AdvisorBatchResponse
from app.services.advisor_service import (
    AdvisorOwnerMismatchError,
    AdvisorUnavailableError,
    get_advisor_library,
    get_advisor_signals_batch,
)

router = APIRouter()


@router.get("/profile/{username}/advisor")
def read_advisor_library(username: str, refresh: bool = Query(False)):
    try:
        return get_advisor_library(username, force=refresh).model_dump()
    except AdvisorOwnerMismatchError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except AdvisorUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/psnprofiles/advisor")
def read_advisor_signals(
    request: AdvisorBatchRequest,
    cached_only: bool = Query(False),
):
    return AdvisorBatchResponse(
        results=get_advisor_signals_batch(
            request.candidates,
            cache_only=cached_only,
        )
    ).model_dump()
