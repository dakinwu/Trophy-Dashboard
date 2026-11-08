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
            title_icon_url="https://example/game.png",
            earned_trophies=SimpleNamespace(
                platinum=1,
                gold=0,
                silver=0,
                bronze=0,
            ),
            title_name="TUNIC™ (PS5)",
            title_platform=[SimpleNamespace(value="PS5")],
            np_communication_id="NPWR12345_00",
            last_updated_datetime=datetime(2026, 7, 25, tzinfo=timezone.utc),
            progress=100,
        )

    def trophy_summary(self):
        return SimpleNamespace(
            trophy_level=321,
            progress=64,
            earned_trophies=SimpleNamespace(
                platinum=1,
                gold=2,
                silver=3,
                bronze=4,
            ),
        )

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
                trophy_id=1,
                earned=True,
                earned_date_time=datetime(2026, 7, 25, tzinfo=timezone.utc),
                trophy_earn_rate=12.5,
                trophy_rarity=SimpleNamespace(name="VERY_RARE"),
                trophy_icon_url="https://example/trophy.png",
                trophy_name="What now?",
                trophy_detail="Earn every trophy.",
                trophy_type=SimpleNamespace(name="PLATINUM"),
                trophy_group_id="default",
            ),
            SimpleNamespace(
                trophy_id=2,
                earned=False,
                earned_date_time=None,
                trophy_earn_rate=82.0,
                trophy_rarity=SimpleNamespace(name="COMMON"),
                trophy_icon_url="https://example/locked.png",
                trophy_name="Still hidden",
                trophy_detail="Keep exploring.",
                trophy_type=SimpleNamespace(name="BRONZE"),
                trophy_group_id="001",
            ),
        ]


def test_platinum_gallery_uses_exact_title_id_artwork_without_refreshing_statistics(tmp_path, monkeypatch):
    cache = FileCache(tmp_path)
    me = FakeMe()
    monkeypatch.setattr(psn_service.settings, "psn_npsso", "test-token")
    monkeypatch.setattr(psn_service, "_client", lambda _: me)
    icon = "https://psnobj.prod.dl.playstation.net/psnobj/NPWR12345_00/icon.PNG"
    cache.save("psn_title_v2/old", {"trophies": [{
        "game": "Localized Game", "title": "What now?", "grade": "Platinum",
        "icon_url": icon, "timestamp": "2020-01-01T00:00:00Z",
        "rarity_percent": "1%",
    }]})

    gallery = psn_service.build_platinum_gallery_from_psn("TestPlayer", cache)

    assert gallery.complete is True
    assert gallery.total_count == 1
    assert gallery.trophies[0].icon_url == icon
    assert gallery.trophies[0].game == me.title.title_name
    assert gallery.trophies[0].timestamp == ""
    assert me.trophy_calls == 0
    assert me.title_stats_calls == 0


def test_platinum_gallery_fetches_missing_artwork_only(tmp_path, monkeypatch):
    cache = FileCache(tmp_path)
    me = FakeMe()
    monkeypatch.setattr(psn_service.settings, "psn_npsso", "test-token")
    monkeypatch.setattr(psn_service, "_client", lambda _: me)

    gallery = psn_service.build_platinum_gallery_from_psn("TestPlayer", cache)

    assert gallery.complete
    assert gallery.trophies[0].grade == "Platinum"
    assert gallery.trophies[0].timestamp == "2026-07-25T00:00:00+00:00"
    assert me.trophy_calls == 1
    assert me.title_stats_calls == 0


def test_match_playtime_titles_normalises_platform_suffixes():
    result = psn_service._match_playtime_titles(
        [
            {
                "name": "TUNIC",
                "seconds": 45_000,
                "platform": "PS5",
                "title_id": "PPSA01234_00",
            }
        ],
        [("TUNIC™ (PS5)", "PS5")],
    )
    assert result == {"TUNIC™ (PS5)": 45_000}


def test_match_playtime_titles_rejects_different_numbered_sequel():
    result = psn_service._match_playtime_titles(
        [
            {
                "name": "Resident Evil 3",
                "seconds": 10_000,
                "platform": "PS5",
                "title_id": "PPSA01234_00",
            }
        ],
        [("Resident Evil 2", "PS5")],
    )
    assert result == {}


def test_match_playtime_titles_keeps_same_name_cross_gen_versions_separate():
    ps5 = SimpleNamespace(
        title_name="Resident Evil Village",
        title_platform=[SimpleNamespace(value="PS5")],
    )
    ps4 = SimpleNamespace(
        title_name="Resident Evil Village",
        title_platform=[SimpleNamespace(value="PS4")],
    )
    display_names = psn_service._display_title_names([ps5, ps4])

    result = psn_service._match_playtime_titles(
        [
            {
                "name": "Resident Evil Village",
                "seconds": 66_449,
                "platform": "PS5",
                "title_id": "PPSA01559_00",
            },
            {
                "name": "Resident Evil Village",
                "seconds": 3_834,
                "platform": "PS4",
                "title_id": "CUSA18045_00",
            },
        ],
        list(zip(display_names, ["PS5", "PS4"], strict=True)),
    )

    assert display_names == [
        "Resident Evil Village (PS5)",
        "Resident Evil Village (PS4)",
    ]
    assert result == {
        "Resident Evil Village (PS5)": 66_449,
        "Resident Evil Village (PS4)": 3_834,
    }


def test_build_profile_caches_title_stats_and_trophies(monkeypatch, tmp_path):
    me = FakeMe()
    monkeypatch.setattr(psn_service, "_client", lambda _npsso: me)
    cache = FileCache(tmp_path)

    first = psn_service.build_profile_from_psn("token", cache=cache)
    second = psn_service.build_profile_from_psn("token", cache=cache)

    assert first is not None
    assert second is not None
    assert first.profile_summary.stats["Level"] == "321"
    assert first.profile_summary.stats["Level Progress"] == "64%"
    assert first.profile_summary.stats["Games Played"] == "1"
    assert first.profile_summary.stats["Completed Games"] == "1"
    assert first.profile_summary.stats["Playtime"] == "12h"
    assert first.game_playtime_seconds == {"TUNIC™ (PS5)": 45_000}
    assert first.profile_summary.total_trophies.platinum == 1
    assert first.trophy_log[0].platforms == ["PS5"]
    assert first.trophy_log[0].rarity_source == "psn"
    assert first.trophy_log[0].psn_rarity_percent == "12.5%"
    assert first.trophy_log[0].is_dlc is False
    assert me.title_stats_calls == 1
    assert me.trophy_calls == 1


def test_build_public_profile_skips_private_playtime_and_scopes_cache(
    monkeypatch,
    tmp_path,
):
    user = FakeMe()
    monkeypatch.setattr(
        psn_service,
        "_public_user",
        lambda _npsso, _online_id: user,
    )
    cache = FileCache(tmp_path)

    first = psn_service.build_profile_from_psn(
        "token",
        online_id="PublicUser",
        cache=cache,
    )
    second = psn_service.build_profile_from_psn(
        "token",
        online_id="PublicUser",
        cache=cache,
    )

    assert first is not None
    assert second is not None
    assert first.game_playtime_seconds == {}
    assert "Playtime" not in first.profile_summary.stats
    assert user.title_stats_calls == 0
    assert user.trophy_calls == 1


def test_build_public_profile_summary_lists_platinum_games(monkeypatch):
    user = FakeMe()
    monkeypatch.setattr(
        psn_service,
        "_public_user",
        lambda _npsso, _online_id: user,
    )

    data = psn_service.build_public_profile_summary_from_psn(
        "PublicUser",
        "token",
    )

    assert data is not None
    assert data.summary_only is True
    assert data.trophy_log == []
    assert data.profile_summary.total_trophies.total == 10
    assert data.profile_summary.total_trophies.platinum == 1
    assert data.profile_summary.stats["Level Progress"] == "64%"
    assert data.profile_summary.stats["Completed Games"] == "1"
    assert len(data.platinum_games) == 1
    assert data.platinum_games[0].game.startswith("TUNIC")
    assert user.trophy_calls == 0


def test_build_game_detail_keeps_unearned_trophies_and_caches(monkeypatch, tmp_path):
    me = FakeMe()
    monkeypatch.setattr(psn_service, "_client", lambda _npsso: me)
    cache = FileCache(tmp_path)

    first = psn_service.build_game_detail_from_psn(
        "TUNIC™ (PS5)",
        "token",
        cache=cache,
    )
    second = psn_service.build_game_detail_from_psn(
        "TUNIC™ (PS5)",
        "token",
        cache=cache,
    )

    assert first == second
    assert first is not None
    assert first.complete is True
    assert len(first.trophies) == 2
    assert first.trophies[0].earned is True
    assert first.trophies[0].rarity_label == "Very Rare"
    assert first.trophies[1].earned is False
    assert first.trophies[1].timestamp == ""
    assert first.trophies[1].is_dlc is True
    assert me.trophy_calls == 1
