from fastapi.testclient import TestClient

from app.main import app
from app.models import ProfileData, ProfileSummary, TrophyCounts, Trophy
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
    monkeypatch.setattr(profile_api, "get_profile", lambda username, force=False: _sample())
    resp = client.get("/api/profile/TestUser")
    assert resp.status_code == 200
    assert resp.json()["profile_summary"]["username"] == "TestUser"
    assert len(resp.json()["trophy_log"]) == 1


def test_get_profile_404(monkeypatch):
    monkeypatch.setattr(profile_api, "get_profile", lambda username, force=False: None)
    resp = client.get("/api/profile/Ghost")
    assert resp.status_code == 404
