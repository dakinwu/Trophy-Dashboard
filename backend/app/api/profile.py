import asyncio
import json
import threading

import requests
from fastapi import APIRouter, HTTPException, Query
from sse_starlette.sse import EventSourceResponse

from app.services.http import PSNProfilesFetchError
from app.services.profile_service import get_game_detail, get_platinum_gallery, get_profile

router = APIRouter()


@router.get("/profile/{username}/platinums")
def read_platinum_gallery(username: str, refresh: bool = Query(False)):
    try:
        gallery = get_platinum_gallery(username, force=refresh)
    except Exception:
        raise HTTPException(status_code=503, detail="暫時無法更新白金清單，請稍後重試。") from None
    if gallery is None:
        raise HTTPException(status_code=503, detail="此玩家的官方白金清單目前無法取得。")
    return gallery.model_dump()


@router.get("/profile/{username}")
def read_profile(username: str, refresh: bool = Query(False)):
    try:
        data = get_profile(username, force=refresh)
    except (requests.exceptions.RequestException, PSNProfilesFetchError):
        raise HTTPException(status_code=502, detail="Error fetching profile from PSNProfiles.")
    if data is None:
        raise HTTPException(status_code=404, detail=f"Profile '{username}' not found or is private.")
    return data.model_dump()


@router.get("/profile/{username}/game")
def read_game_detail(username: str, game: str = Query(..., min_length=1)):
    data = get_game_detail(username, game)
    if data is None:
        raise HTTPException(
            status_code=404,
            detail=f"Game '{game}' was not found for profile '{username}'.",
        )
    return data.model_dump()


@router.get("/profile/{username}/stream")
async def stream_profile(username: str):
    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def on_progress(page: int, total: int) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, {"type": "progress", "page": page, "total": total})

    stop_event = threading.Event()

    async def run() -> None:
        try:
            data = await asyncio.to_thread(
                get_profile,
                username,
                force=False,
                on_progress=on_progress,
                should_stop=stop_event.is_set,
            )
            loop.call_soon_threadsafe(
                queue.put_nowait, {"type": "done", "found": data is not None}
            )
        except Exception as exc:  # surfaced to the client as an error event
            loop.call_soon_threadsafe(queue.put_nowait, {"type": "error", "error": str(exc)})

    async def event_gen():
        task = asyncio.create_task(run())
        try:
            while True:
                msg = await queue.get()
                kind = msg.pop("type")
                yield {"event": kind, "data": json.dumps(msg)}
                if kind in ("done", "error"):
                    break
        finally:
            stop_event.set()
            await task

    return EventSourceResponse(event_gen())
