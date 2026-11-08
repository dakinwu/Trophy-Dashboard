from tests.conftest import FakeSession, load_fixture
from app.core.cache import FileCache
from app.models import (
    GameTrophyDetail,
    ProfileData,
    ProfileSummary,
    Trophy,
    TrophyCounts,
    PlatinumGallery,
)
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
    assert data.profile_source == "psnprofiles"
    assert data.cache_status == "live"
    assert data.fetched_at is not None
    # Cached file exists and a second call (with a session that would yield
    # nothing) still returns cached data.
    again = profile_service.get_profile("TestUser", session=FakeSession(), cache=cache)
    assert again is not None
    assert len(again.trophy_log) == 2
    assert again.profile_source == "psnprofiles"
    assert again.cache_status == "cached"
    assert again.fetched_at == data.fetched_at


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


def test_get_profile_ignores_cached_summary_without_trophy_log(
    tmp_path,
    monkeypatch,
):
    cache = FileCache(tmp_path)
    empty_profile = ProfileData(
        profile_summary=ProfileSummary(
            username="PublicUser",
            total_trophies=TrophyCounts(total=100, platinum=5),
        ),
        trophy_log=[],
    )
    official_profile = ProfileData(
        profile_summary=ProfileSummary(
            username="PublicUser",
            total_trophies=TrophyCounts(total=1, platinum=1),
        ),
        trophy_log=[
            Trophy(
                game="Test Game",
                platforms=["PS5"],
                icon_url="icon.png",
                title="Platinum",
                timestamp="2026-01-01T00:00:00Z",
                rarity_percent="5.0%",
                rarity_source="psn",
                psn_rarity_percent="5.0%",
                grade="Platinum",
            )
        ],
    )
    cache.save("profile_v3/publicuser", empty_profile.model_dump())
    monkeypatch.setattr(profile_service.settings, "psn_npsso", "token")
    monkeypatch.setattr(profile_service, "_token_owner_online_id", lambda: "Owner")

    calls: list[str | None] = []

    def build(online_id):
        calls.append(online_id)
        return official_profile

    monkeypatch.setattr(
        profile_service,
        "build_public_profile_summary_from_psn",
        build,
    )

    data = profile_service.get_profile("PublicUser", cache=cache)

    assert data is not None
    assert len(data.trophy_log) == 1
    assert data.trophy_log[0].grade == "Platinum"
    assert calls == ["PublicUser"]


def test_get_profile_does_not_cache_empty_scraper_log(tmp_path):
    cache = FileCache(tmp_path)
    data = profile_service.get_profile(
        "TestUser",
        session=FakeSession(
            summary_html=load_fixture("profile_summary.html"),
            log_pages=[],
        ),
        cache=cache,
    )

    assert data is None
    assert cache.load("profile_v3/testuser", 60) is None


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


def test_get_profile_adds_cached_psnprofiles_rarity_without_scraping(tmp_path):
    cache = FileCache(tmp_path)
    profile = ProfileData(
        profile_summary=ProfileSummary(
            username="TestUser",
            total_trophies=TrophyCounts(total=1),
        ),
        trophy_log=[
            Trophy(
                game="Test Game (PS5)",
                platforms=["PS5"],
                icon_url="icon.png",
                title="First Trophy",
                timestamp="1st Jan 2026 1:00:00 pm",
                rarity_percent="2.0%",
                rarity_source="psn",
                psn_rarity_percent="2.0%",
                grade="Bronze",
                trophy_id=0,
            )
        ],
    )
    cache.save("profile_v3/testuser", profile.model_dump())
    cache.save(
        "psnprofiles_trophies_v6/example",
        {
            "title": "Test Game",
            "platform": "PS5",
            "trophies": [
                {
                    "trophy_id": 0,
                    "title": "First Trophy",
                    "psnprofiles_rarity_percent": "2.0%",
                    "rarity_percentages": ["2.0%", "12.34%"],
                }
            ],
        },
    )

    data = profile_service.get_profile("TestUser", cache=cache)

    assert data is not None
    assert data.trophy_log[0].psn_rarity_percent == "2.0%"
    assert data.trophy_log[0].psnprofiles_rarity_percent == "12.34%"


def test_get_profile_reuses_recent_official_icon_cache_for_psnprofiles_rows(
    tmp_path,
    monkeypatch,
):
    cache = FileCache(tmp_path)
    profile = ProfileData(
        profile_summary=ProfileSummary(
            username="TestUser",
            total_trophies=TrophyCounts(total=1),
        ),
        trophy_log=[
            Trophy(
                game="Test Game (PS5)",
                platforms=["PS5"],
                icon_url="https://img.psnprofiles.com/trophy/s/1/blocked.png",
                title="First Trophy",
                timestamp="1st Jan 2026 1:00:00 pm",
                rarity_percent="2.0%",
                rarity_source="psnprofiles",
                psnprofiles_rarity_percent="2.0%",
                grade="Bronze",
                trophy_id=0,
            )
        ],
    )
    cache.save("profile_v3/testuser", profile.model_dump())
    cache.save(
        "psn_title_v2/official",
        {
            "trophies": [
                {
                    "game": "Test Game",
                    "title": "First Trophy",
                    "icon_url": (
                        "https://image.api.playstation.com/trophy/np/TEST/ICON.PNG"
                    ),
                }
            ]
        },
    )
    data = profile_service.get_profile("TestUser", cache=cache)

    assert data is not None
    assert data.trophy_log[0].icon_url.startswith(
        "https://image.api.playstation.com/"
    )


def test_partial_fallback_retains_gallery_for_same_user_without_changing_log(tmp_path):
    cache = FileCache(tmp_path)

    def platinum(title, stamp):
        return Trophy(game="Game", title=title, grade="Platinum", timestamp=stamp,
                      icon_url="https://image.api.playstation.com/trophy/np/T/icon.PNG",
                      rarity_percent="1%")

    older = platinum("Old platinum", "2026-01-01T00:00:00Z")
    recent = platinum("New platinum", "2026-02-01T00:00:00Z")
    complete = ProfileData(profile_summary=ProfileSummary(
        username="TestUser", total_trophies=TrophyCounts(total=2, platinum=2)),
        trophy_log=[recent, older])
    profile_service._with_cached_official_icons(complete, cache)
    partial = ProfileData(profile_summary=complete.profile_summary, trophy_log=[recent])
    cache.save("profile_v3/testuser", partial.model_dump())

    data = profile_service.get_profile("TestUser", cache=cache)

    assert len(data.trophy_log) == 1
    assert [t.title for t in data.platinum_trophies] == ["New platinum", "Old platinum"]
    other = ProfileData(profile_summary=ProfileSummary(
        username="OtherUser", total_trophies=TrophyCounts(total=2, platinum=2)),
        trophy_log=[recent])
    profile_service._with_cached_official_icons(other, cache)
    assert len(other.platinum_trophies) == 1


def test_expired_gallery_remains_available_when_sony_is_unreachable(tmp_path, monkeypatch):
    import os
    import time

    cache = FileCache(tmp_path)
    gallery = PlatinumGallery(username="TestUser", trophies=[], total_count=0,
                              fetched_at="2026-01-01T00:00:00Z", complete=True)
    cache.save("psn_platinum_gallery_v1/testuser", gallery.model_dump())
    old_time = time.time() - 10 * 86400
    os.utime(tmp_path / "psn_platinum_gallery_v1__testuser.json", (old_time, old_time))

    def unavailable(*_args):
        raise ConnectionError("offline")

    monkeypatch.setattr(profile_service, "build_platinum_gallery_from_psn", unavailable)
    result = profile_service.get_platinum_gallery("TestUser", cache=cache)
    assert result.complete
    assert result.cache_status == "cached"
    assert result.fetched_at == gallery.fetched_at
