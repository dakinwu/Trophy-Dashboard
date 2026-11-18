from fastapi.testclient import TestClient

from app.main import app
from app.models import (
    GameTrophyDetail,
    ProfileData,
    ProfileSummary,
    Trophy,
    TrophyCounts,
)
import app.api.profile as profile_api

client = TestClient(app)


def _sample() -> ProfileData:
    return ProfileData(
        profile_summary=ProfileSummary(
            username="TestUser", total_trophies=TrophyCounts(total=1)
        ),
        trophy_log=[
            Trophy(game="G", icon_url="u", title="T", timestamp="ts", rarity_percent="1%", grade="Gold")
        ],
    )


def test_get_profile_200(monkeypatch):
    monkeypatch.setattr(profile_api, "get_profile", lambda username, **_: _sample())
    resp = client.get("/api/profile/TestUser")
    assert resp.status_code == 200
    assert resp.json()["profile_summary"]["username"] == "TestUser"
    assert len(resp.json()["trophy_log"]) == 1


def test_get_profile_404(monkeypatch):
    monkeypatch.setattr(profile_api, "get_profile", lambda username, **_: None)
    resp = client.get("/api/profile/Ghost")
    assert resp.status_code == 404


def test_get_game_detail_200(monkeypatch):
    monkeypatch.setattr(
        profile_api,
        "get_game_detail",
        lambda username, game: GameTrophyDetail(
            game=game,
            display_name="Test Game",
            platforms=["PS5"],
            trophies=[
                Trophy(
                    game=game,
                    platforms=["PS5"],
                    icon_url="u",
                    title="T",
                    timestamp="",
                    earned=False,
                    rarity_percent="10%",
                    grade="Bronze",
                )
            ],
            complete=True,
            source="psn",
        ),
    )
    resp = client.get(
        "/api/profile/TestUser/game",
        params={"game": "Test Game (PS5)"},
    )
    assert resp.status_code == 200
    assert resp.json()["complete"] is True
    assert resp.json()["trophies"][0]["earned"] is False


def test_get_profile_serves_stale_data_while_refreshing(monkeypatch):
    calls: list[dict] = []

    def fake(username, **kwargs):
        calls.append(kwargs)
        data = _sample()
        data.cache_status = "cached"
        data.refreshing = True
        return data

    monkeypatch.setattr(profile_api, "get_profile", fake)
    resp = client.get("/api/profile/TestUser")

    assert resp.status_code == 200
    assert resp.json()["refreshing"] is True
    assert calls == [{"force": False, "background_refresh": True}]
