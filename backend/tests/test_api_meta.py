from fastapi.testclient import TestClient

import app.api.enrich as enrich_api
from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_psnine_redirect_uses_simplified_chinese_name(monkeypatch):
    monkeypatch.setattr(
        enrich_api, "get_psnine_title", lambda game: "生化危机 村庄"
    )
    resp = client.get(
        "/api/psnine",
        params={"game": "Resident Evil Village"},
        follow_redirects=False,
    )
    assert resp.status_code == 307
    assert (
        resp.headers["location"]
        == "https://www.psnine.com/psngame?title=%E7%94%9F%E5%8C%96%E5%8D%B1%E6%9C%BA%20%E6%9D%91%E5%BA%84"
    )


def test_psnprofiles_guide_returns_enrichment(monkeypatch):
    monkeypatch.setattr(
        enrich_api,
        "get_psnprofiles_guide",
        lambda game: {
            "title": f"{game} Trophy Guide",
            "guide_url": "https://psnprofiles.com/guide/1234-game-trophy-guide",
            "difficulty": "4/10",
            "platinum_time": "40-50 hours",
        },
    )
    resp = client.get("/api/psnprofiles/guide", params={"game": "God of War"})
    assert resp.status_code == 200
    assert resp.json()["difficulty"] == "4/10"


def test_psnprofiles_stats_returns_rankings(monkeypatch):
    monkeypatch.setattr(
        enrich_api,
        "get_psnprofiles_stats",
        lambda username: {
            "world_rank": 174309,
            "country_rank": 4321,
            "country_label": "Country Rank",
            "completion": "99.9%",
            "profile_url": f"https://psnprofiles.com/{username}",
        },
    )
    resp = client.get("/api/psnprofiles/stats", params={"username": "TestUser"})
    assert resp.status_code == 200
    assert resp.json()["world_rank"] == 174309
    assert resp.json()["country_rank"] == 4321


def test_psnprofiles_trophies_returns_per_trophy_rarity(monkeypatch):
    monkeypatch.setattr(
        enrich_api,
        "get_psnprofiles_trophies",
        lambda game, platform: {
            "title": game,
            "platform": platform,
            "game_url": "https://psnprofiles.com/trophies/123-test-game",
            "trophies": [
                {
                    "title": "First Blood",
                    "psnprofiles_rarity_percent": "2.5%",
                    "rarity_label": "Ultra Rare",
                    "trophy_url": "https://psnprofiles.com/trophy/123-test-game/1-first-blood",
                }
            ],
        },
    )
    resp = client.get(
        "/api/psnprofiles/trophies",
        params={"game": "Test Game", "platform": "PS5"},
    )
    assert resp.status_code == 200
    assert resp.json()["trophies"][0]["psnprofiles_rarity_percent"] == "2.5%"
