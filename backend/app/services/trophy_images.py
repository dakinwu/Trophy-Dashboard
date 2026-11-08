"""Durable, bounded storage for public Sony trophy artwork (not account data)."""

import hashlib
import os
import tempfile
import threading
from pathlib import Path
from urllib.parse import urlsplit

import requests

from app.core.cache import FileCache

_HOST_PATHS = {
    "image.api.playstation.com": "/trophy/",
    "psnobj.prod.dl.playstation.net": "/psnobj/",
}
_MAX_BYTES = 5 * 1024 * 1024
_LOCKS = [threading.Lock() for _ in range(32)]
_DOWNLOADS = threading.BoundedSemaphore(4)


class ImageUnavailableError(RuntimeError):
    pass


def is_official_trophy_image(url: str) -> bool:
    try:
        parsed = urlsplit(url)
        prefix = _HOST_PATHS.get(parsed.hostname or "")
        return bool(
            len(url) <= 2048 and parsed.scheme == "https" and prefix
            and parsed.path.startswith(prefix)
            and parsed.path.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
            and not parsed.username and not parsed.password
            and parsed.port in (None, 443) and not parsed.query and not parsed.fragment
        )
    except ValueError:
        return False


def image_media_type(data: bytes) -> str | None:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def get_official_image(url: str, cache: FileCache) -> tuple[Path, str]:
    """Download once, then serve the file indefinitely, even while offline.

    Only two fixed public Sony hosts are accepted; redirects, HTML challenge
    pages, oversized responses and failures are never stored as artwork.
    """
    if not is_official_trophy_image(url):
        raise ValueError("Unsupported trophy image URL")
    digest = hashlib.sha256(url.encode()).hexdigest()
    directory = cache.base_dir / "trophy_images"
    path = directory / f"{digest}.img"
    with _LOCKS[int(digest[:2], 16) % len(_LOCKS)]:
        if path.is_file():
            with path.open("rb") as file:
                media_type = image_media_type(file.read(16))
            if media_type:
                return path, media_type
        failure_key = f"trophy_image_failure/{digest}"
        if cache.load(failure_key, 60) is not None:
            raise ImageUnavailableError("Official trophy image temporarily unavailable")
        temp_path = None
        try:
            with _DOWNLOADS, requests.get(
                url, timeout=(4, 12), stream=True, allow_redirects=False,
            ) as response:
                if response.status_code != 200:
                    raise ImageUnavailableError("Official trophy image request failed")
                if int(response.headers.get("Content-Length") or 0) > _MAX_BYTES:
                    raise ImageUnavailableError("Official trophy image exceeds size limit")
                data = bytearray()
                for chunk in response.iter_content(64 * 1024):
                    data.extend(chunk)
                    if len(data) > _MAX_BYTES:
                        raise ImageUnavailableError("Official trophy image exceeds size limit")
                media_type = image_media_type(data)
                if media_type is None:
                    raise ImageUnavailableError("Official source did not return an image")
            directory.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=directory, delete=False) as file:
                temp_path = Path(file.name)
                file.write(data)
            os.replace(temp_path, path)
            return path, media_type
        except (requests.RequestException, OSError, ValueError, ImageUnavailableError) as exc:
            cache.save(failure_key, {"unavailable": True})
            raise ImageUnavailableError("Official trophy image temporarily unavailable") from exc
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
