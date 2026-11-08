import asyncio
import os
import time

import pytest

from app.core.cache import FileCache
from app.models import AdvisorCandidate
from app.services import gemini_title_service as titles
from app.services import psnprofiles_trophies_service as lists
from app.services.http import NodriverSession
from tests.conftest import FakeResponse


@pytest.mark.parametrize("name", ["F1 25", "F1® 25", "H1Z1"])
def test_alphanumeric_english_titles_do_not_consume_gemini(name, tmp_path, monkeypatch):
    monkeypatch.setattr(titles.settings, "gemini_api_key", "test-only")
    monkeypatch.setattr(titles.requests, "post", lambda *_a, **_k: pytest.fail("Gemini called"))
    candidate = AdvisorCandidate(game=name, platform="PS5")
    result = titles.resolve_advisor_titles([candidate], cache=FileCache(tmp_path))
    assert titles.is_english_search_title(result[titles.candidate_key(candidate)].search_title)


def test_search_filters_unsafe_and_wrong_platform_before_ranking():
    html = '''<table><tr><td><a href="/trophies/1-alan-wake">Alan Wake</a>PS5</td></tr>
      <tr><td><a href="/trophies/2-alan-wake-2">Alan Wake 2 Deluxe Edition</a>PS5</td></tr>
      <tr><td><a href="/trophies/3-alan-wake-2">Alan Wake 2</a>PS4</td></tr></table>'''
    result = lists.parse_game_search(html, "Alan Wake 2", "PS5")
    assert result["game_url"].endswith("/2-alan-wake-2")


def test_browser_does_not_accept_previous_page_during_navigation():
    class Tab:
        def __init__(self):
            self.polls = 0

        async def evaluate(self, *_args, **_kwargs):
            self.polls += 1
            return {"url": "https://psnprofiles.com/search/games?q=" +
                    ("Old" if self.polls == 1 else "Erica"), "readyState": "complete"}

        async def get_content(self):
            title = "Old" if self.polls == 1 else "Erica"
            return f'<title>Search</title><table class="zebra"><tr><td><a href="/trophies/1-game">{title}</a></td></tr></table>'

        async def sleep(self, _seconds):
            pass

    class Browser:
        def __init__(self):
            self.tab = Tab()

        async def get(self, _url):
            return self.tab

    session = NodriverSession()
    session._browser = Browser()
    response = asyncio.run(session._get("https://psnprofiles.com/search/games?q=Erica", 2))
    assert "Erica" in response.text
    assert "Old" not in response.text
    assert session._browser.tab.polls >= 2


def _old_success(cache):
    import hashlib
    key = "psnprofiles_trophies_v7/" + hashlib.sha256(b"test game:PS5").hexdigest()
    data = {"title": "Test Game", "platform": "PS5",
            "game_url": "https://psnprofiles.com/trophies/123-test-game",
            "trophies": [{"title": "First", "trophy_id": 0}], "owners": 123}
    cache.save(key, data)
    path = cache._path(key)
    old_time = time.time() - 90 * 86400
    os.utime(path, (old_time, old_time))
    return path


def test_expired_success_is_restored_without_network_and_keeps_real_age(tmp_path, monkeypatch):
    cache = FileCache(tmp_path)
    path = _old_success(cache)
    before = path.stat().st_mtime
    monkeypatch.setattr(lists, "create_session", lambda: pytest.fail("Browser opened"))
    data = lists.get_psnprofiles_trophies("Test Game", "PS5", cache=cache, cache_only=True)
    assert data["cache_status"] == "stale"
    assert data["fetched_at"]
    assert data["owners"] == 123
    assert path.stat().st_mtime == before


def test_found_trophy_page_is_retried_without_searching_or_renaming_again(tmp_path):
    from tests.conftest import load_fixture

    class Session:
        def __init__(self):
            self.urls = []
            self.trophy_calls = 0

        def get(self, url, **_kwargs):
            self.urls.append(url)
            if "/search/games" in url:
                return FakeResponse(load_fixture("psnprofiles_game_search.html"))
            self.trophy_calls += 1
            return FakeResponse("<table></table>" if self.trophy_calls == 1 else
                                load_fixture("psnprofiles_trophy_page.html"))

    session = Session()
    data = lists.get_psnprofiles_trophies("Resident Evil Village", "PS5",
                                        session=session, cache=FileCache(tmp_path))
    assert data["trophies"]
    assert session.trophy_calls == 2
    assert sum("/search/games" in url for url in session.urls) == 1


def test_failed_refresh_keeps_previous_success(tmp_path):
    cache = FileCache(tmp_path)
    path = _old_success(cache)
    before = path.read_bytes()

    class Session:
        def get(self, *_args, **_kwargs):
            return FakeResponse("<title>Search</title><table></table>")

    data = lists.get_psnprofiles_trophies("Test Game", "PS5", cache=cache, session=Session())
    assert data["cache_status"] == "stale"
    assert data["refresh_error"]
    assert path.read_bytes() == before


def test_same_verified_title_is_valid_on_explicit_title_recheck(tmp_path, monkeypatch):
    candidate = AdvisorCandidate(game="測試遊戲", platform="PS5")
    monkeypatch.setattr(titles.settings, "gemini_api_key", "test-only")
    monkeypatch.setattr(titles, "_request_resolutions", lambda *_args, **_kwargs: {
        "0": {"english_title": "Test Game", "is_trial": False},
    })
    result = titles.resolve_advisor_titles([candidate], cache=FileCache(tmp_path),
        retry_attempts={titles.candidate_key(candidate): "Test Game"})
    assert result[titles.candidate_key(candidate)].error is None


def test_default_analysis_never_uses_gemini_for_english_search_failure(tmp_path, monkeypatch):
    from app.services import advisor_service
    from contextlib import nullcontext

    monkeypatch.setattr(titles.settings, "gemini_api_key", "test-only")
    monkeypatch.setattr(titles.requests, "post", lambda *_a, **_k: pytest.fail("Gemini called"))
    monkeypatch.setattr(advisor_service, "create_session", lambda: nullcontext(object()))
    monkeypatch.setattr(advisor_service, "get_psnprofiles_trophies", lambda *_a, **_k: None)
    result = advisor_service.get_advisor_signals_batch(
        [AdvisorCandidate(game="Erica", platform="PS4")], cache=FileCache(tmp_path),
    )[0]
    assert result.error_stage == "search"
    assert "Gemini" not in result.error


def test_one_empty_trophy_table_does_not_block_remaining_games(tmp_path, monkeypatch):
    from app.services import advisor_service
    from contextlib import nullcontext

    monkeypatch.setattr(advisor_service, "create_session", lambda: nullcontext(object()))
    def fetch(game, platform, **_kwargs):
        if game == "First Game":
            raise lists.PSNProfilesTrophyReadError("已找到遊戲，但表格未完成載入。")
        return {"title": game, "platform": platform,
                "game_url": "https://psnprofiles.com/trophies/2-second"}
    monkeypatch.setattr(advisor_service, "get_psnprofiles_trophies", fetch)
    results = advisor_service.get_advisor_signals_batch([
        AdvisorCandidate(game="First Game", platform="PS4"),
        AdvisorCandidate(game="Second Game", platform="PS4"),
    ], cache=FileCache(tmp_path), allow_title_api=False)
    assert results[0].error_stage == "trophy_page"
    assert results[1].signals.title == "Second Game"


def test_manual_challenge_is_not_automatically_retried(tmp_path):
    from app.services.http import PSNProfilesChallengeError

    class Session:
        calls = 0
        def get(self, *_args, **_kwargs):
            self.calls += 1
            raise PSNProfilesChallengeError("需要手動驗證")
    session = Session()
    with pytest.raises(PSNProfilesChallengeError):
        lists.get_psnprofiles_trophies("Erica", "PS4", cache=FileCache(tmp_path), session=session)
    assert session.calls == 1
