import os
import time

import pytest
from fastapi.testclient import TestClient

from app.core.cache import FileCache
from app.models import Trophy
from app.services.profile_service import _replace_blocked_official_icons
from app.services import trophy_images
from app.main import app
from app.config import settings


def _trophy(game="Game", title="Platinum"):
    return Trophy(
        game=game, title=title, grade="Platinum", timestamp="",
        icon_url="https://img.psnprofiles.com/trophy/s/123/test.png",
        rarity_percent="1%",
    )


def test_ps5_artwork_is_recovered_even_when_statistics_cache_has_expired(tmp_path):
    cache = FileCache(tmp_path)
    official = "https://psnobj.prod.dl.playstation.net/psnobj/NPWR123_00/icon.PNG"
    cache.save("psn_title_v2/ps5", {"trophies": [
        {"game": "Game", "title": "Platinum", "icon_url": official},
    ]})
    old_time = time.time() - 120 * 86400
    os.utime(tmp_path / "psn_title_v2__ps5.json", (old_time, old_time))
    trophies = [_trophy()]

    assert _replace_blocked_official_icons(trophies, cache) == 1
    assert trophies[0].icon_url == official


def test_generic_trophy_title_does_not_use_another_games_artwork(tmp_path):
    cache = FileCache(tmp_path)
    cache.save("psn_title_v2/other", {"trophies": [
        {"game": "Other Game", "title": "Platinum",
         "icon_url": "https://image.api.playstation.com/trophy/np/OTHER/icon.PNG"},
    ]})
    trophies = [_trophy()]

    assert _replace_blocked_official_icons(trophies, cache) == 0
    assert "img.psnprofiles.com" in trophies[0].icon_url


@pytest.mark.parametrize("url", [
    "http://127.0.0.1/private.png",
    "https://image.api.playstation.com.evil.test/trophy/x.png",
    "https://image.api.playstation.com/other/x.png",
    "https://image.api.playstation.com:123/trophy/x.png",
    "https://user:password@image.api.playstation.com/trophy/x.png",
])
def test_image_endpoint_rejects_unapproved_sources(url, monkeypatch):
    monkeypatch.setattr(trophy_images.requests, "get", lambda *_a, **_k: pytest.fail("Network request"))
    response = TestClient(app).get("/api/images/official", params={"url": url})
    assert response.status_code == 400


class _ImageResponse:
    status_code = 200
    headers = {"Content-Type": "image/png"}
    data = b"\x89PNG\r\n\x1a\nexample-image-bytes"

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        pass

    def iter_content(self, _chunk_size):
        yield self.data


def test_image_endpoint_keeps_original_bytes_after_restart_and_while_offline(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "cache_dir", str(tmp_path))
    calls = []

    def download(url, **kwargs):
        calls.append(url)
        assert kwargs["allow_redirects"] is False
        return _ImageResponse()

    monkeypatch.setattr(trophy_images.requests, "get", download)
    url = "https://psnobj.prod.dl.playstation.net/psnobj/NPWR123_00/icon.PNG"
    first = TestClient(app).get("/api/images/official", params={"url": url})
    assert first.status_code == 200
    assert first.content == _ImageResponse.data
    path = next((tmp_path / "trophy_images").glob("*.img"))
    old_time = time.time() - 365 * 86400
    os.utime(path, (old_time, old_time))
    monkeypatch.setattr(trophy_images.requests, "get", lambda *_a, **_k: pytest.fail("Offline"))
    again = TestClient(app).get("/api/images/official", params={"url": url})
    assert again.status_code == 200
    assert again.content == first.content
    assert "immutable" in again.headers["cache-control"]
    assert len(calls) == 1


def test_cloudflare_html_is_not_saved_as_artwork_and_failures_have_cooldown(tmp_path, monkeypatch):
    calls = []

    class HtmlResponse(_ImageResponse):
        data = b"<html>Just a moment...</html>"

    def download(*_args, **_kwargs):
        calls.append(1)
        return HtmlResponse()

    monkeypatch.setattr(trophy_images.requests, "get", download)
    cache = FileCache(tmp_path)
    url = "https://image.api.playstation.com/trophy/np/TEST/icon.PNG"
    for _ in range(2):
        with pytest.raises(trophy_images.ImageUnavailableError):
            trophy_images.get_official_image(url, cache)
    assert not list(tmp_path.glob("trophy_images/*.img"))
    assert calls == [1]
