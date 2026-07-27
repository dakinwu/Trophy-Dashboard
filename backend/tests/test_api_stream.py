from fastapi.testclient import TestClient

from app.main import app
from app.models import ProfileData, ProfileSummary, TrophyCounts
import app.api.profile as profile_api

client = TestClient(app)


def test_stream_emits_progress_then_done(monkeypatch):
    def fake_get_profile(username, *, force=False, on_progress=None, should_stop=None):
        if on_progress:
            on_progress(1, 2)
            on_progress(2, 2)
        return ProfileData(
            profile_summary=ProfileSummary(username=username, total_trophies=TrophyCounts(total=1))
        )

    monkeypatch.setattr(profile_api, "get_profile", fake_get_profile)

    with client.stream("GET", "/api/profile/TestUser/stream") as resp:
        assert resp.status_code == 200
        body = "".join(resp.iter_text())

    assert "event: progress" in body
    assert '"page": 1' in body
    assert '"total": 2' in body
    assert "event: done" in body
    assert '"found": true' in body
