from tests.conftest import FakeSession, load_fixture
from app.core.cache import FileCache
from app.models import GameTrophyDetail
from app.services import profile_service


def _session(pages: int) -> FakeSession:
    return FakeSession(
        summary_html=load_fixture("profile_summary.html"),
        log_pages=[load_fixture("trophy_log_page.html")] * pages,
    )


def test_get_profile_scrapes_and_caches(tmp_path, monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)
    cache = FileCache(tmp_path)
    data = profile_service.get_profile("TestUser", session=_session(2), cache=cache)
    assert data is not None
    assert len(data.trophy_log) == 2
    # Cached file exists and a second call (with a session that would yield
    # nothing) still returns cached data.
    again = profile_service.get_profile("TestUser", session=FakeSession(), cache=cache)
    assert again is not None
    assert len(again.trophy_log) == 2


def test_get_profile_force_bypasses_cache(tmp_path, monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)
    cache = FileCache(tmp_path)
    profile_service.get_profile("TestUser", session=_session(2), cache=cache)
    forced = profile_service.get_profile(
        "TestUser", force=True, session=_session(3), cache=cache
    )
    assert forced is not None
    assert len(forced.trophy_log) == 3


def test_get_profile_none_for_missing(tmp_path):
    cache = FileCache(tmp_path)
    data = profile_service.get_profile(
        "Ghost", session=FakeSession(summary_html="<html></html>"), cache=cache
    )
    assert data is None


def test_get_game_detail_uses_short_cache(tmp_path, monkeypatch):
    cache = FileCache(tmp_path)
    calls = {"count": 0}

    def build(game, cache):
        calls["count"] += 1
        return GameTrophyDetail(
            game=game,
            display_name="Test Game",
            platforms=["PS5"],
            trophies=[],
            complete=True,
            source="psn",
        )

    monkeypatch.setattr(profile_service.settings, "psn_npsso", "token")
    monkeypatch.setattr(profile_service, "_token_owner_online_id", lambda: "TestUser")
    monkeypatch.setattr(profile_service, "build_game_detail_from_psn", build)

    first = profile_service.get_game_detail(
        "TestUser",
        "Test Game (PS5)",
        cache=cache,
    )
    second = profile_service.get_game_detail(
        "TestUser",
        "Test Game (PS5)",
        cache=cache,
    )

    assert first == second
    assert calls["count"] == 1
