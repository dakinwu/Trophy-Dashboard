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
