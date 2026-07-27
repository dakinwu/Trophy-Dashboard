from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.core.cache import FileCache
from app.services import psn_service


class FakeMe:
    online_id = "TestPlayer"

    def __init__(self):
        self.title_stats_calls = 0
        self.trophy_calls = 0
        self.title = SimpleNamespace(
            title_name="TUNIC™ (PS5)",
            title_platform=[SimpleNamespace(value="PS5")],
            np_communication_id="NPWR12345_00",
            last_updated_datetime=datetime(2026, 7, 25, tzinfo=timezone.utc),
        )

    def trophy_summary(self):
        return SimpleNamespace(trophy_level=321)

    def get_profile_legacy(self):
        return {
            "profile": {
                "avatarUrls": [{"avatarUrl": "https://example/avatar.png"}]
            }
        }

    def title_stats(self):
        self.title_stats_calls += 1
        return [
            SimpleNamespace(
                name="TUNIC",
                play_duration=timedelta(hours=12, minutes=30),
            )
        ]

    def trophy_titles(self):
        return [self.title]

    def trophies(self, **_kwargs):
        self.trophy_calls += 1
        return [
            SimpleNamespace(
                earned=True,
                earned_date_time=datetime(2026, 7, 25, tzinfo=timezone.utc),
                trophy_earn_rate=12.5,
                trophy_icon_url="https://example/trophy.png",
                trophy_name="What now?",
                trophy_type=SimpleNamespace(name="PLATINUM"),
            )
        ]


def test_match_playtime_titles_normalises_platform_suffixes():
    result = psn_service._match_playtime_titles(
        {"TUNIC": 45_000},
        ["TUNIC™ (PS5)"],
    )
    assert result == {"TUNIC™ (PS5)": 45_000}


def test_match_playtime_titles_rejects_different_numbered_sequel():
    result = psn_service._match_playtime_titles(
        {"Resident Evil 3": 10_000},
        ["Resident Evil 2"],
    )
    assert result == {}


def test_build_profile_caches_title_stats_and_trophies(monkeypatch, tmp_path):
    me = FakeMe()
    monkeypatch.setattr(psn_service, "_client", lambda _npsso: me)
    cache = FileCache(tmp_path)

    first = psn_service.build_profile_from_psn("token", cache=cache)
    second = psn_service.build_profile_from_psn("token", cache=cache)

    assert first is not None
    assert second is not None
    assert first.profile_summary.stats["Level"] == "321"
    assert first.profile_summary.stats["Playtime"] == "12h"
    assert first.game_playtime_seconds == {"TUNIC™ (PS5)": 45_000}
    assert first.profile_summary.total_trophies.platinum == 1
    assert me.title_stats_calls == 1
    assert me.trophy_calls == 1
