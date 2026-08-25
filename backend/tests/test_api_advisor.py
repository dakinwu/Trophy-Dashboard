from fastapi.testclient import TestClient

import app.api.advisor as advisor_api
from app.main import app
from app.models import AdvisorLibrary

client = TestClient(app)


def test_advisor_api_returns_library(monkeypatch):
    monkeypatch.setattr(
        advisor_api,
        "get_advisor_library",
        lambda username, force=False: AdvisorLibrary(username=username),
    )
    response = client.get("/api/profile/TestUser/advisor")

    assert response.status_code == 200
    assert response.json()["username"] == "TestUser"
    assert response.json()["source"] == "official_psn"


def test_advisor_api_rejects_public_profile(monkeypatch):
    def reject(_username, force=False):
        raise advisor_api.AdvisorOwnerMismatchError("owner only")

    monkeypatch.setattr(advisor_api, "get_advisor_library", reject)
    response = client.get("/api/profile/PublicUser/advisor")

    assert response.status_code == 403
    assert response.json()["detail"] == "owner only"


def test_advisor_batch_is_bounded():
    response = client.post(
        "/api/psnprofiles/advisor",
        json={
            "candidates": [
                {"game": f"Game {index}", "platform": "PS5"}
                for index in range(51)
            ]
        },
    )
    assert response.status_code == 422
