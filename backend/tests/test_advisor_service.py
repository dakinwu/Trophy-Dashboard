import json
from datetime import timedelta
from types import SimpleNamespace

import pytest

from app.core.cache import FileCache
from app.models import AdvisorCandidate
from app.services import advisor_service
from app.services.gemini_title_service import TitleResolution, candidate_key


def _raw_game(title_id: str, name: str, platform: str, membership: str = "NONE"):
    return {
        "titleId": title_id,
        "productId": f"product-{title_id}",
        "conceptId": f"concept-{title_id}",
        "name": name,
        "platform": platform,
        "membership": membership,
        "subscriptionService": None,
        "isDownloadable": True,
        "isPreOrder": False,
        "image": {"url": f"https://example/{title_id}.png"},
    }


class FakeAuthenticator:
    def __init__(self):
        self.calls = 0

    def get(self, **kwargs):
        self.calls += 1
        start = json.loads(kwargs["params"]["variables"])["start"]
        if start == 0:
            games = [
                _raw_game("PPSA00001_00", "Started Game", "PS5"),
                _raw_game("CUSA00002_00", "Finished Game", "PS4", "PS_PLUS"),
            ]
            page_info = {"isLast": False, "offset": 0, "size": 2, "totalCount": 3}
        else:
            games = [_raw_game("PPSA00003_00", "Unplayed Game", "PS5")]
            page_info = {"isLast": True, "offset": 2, "size": 1, "totalCount": 3}
        return {
            "data": {
                "purchasedTitlesRetrieve": {
                    "games": games,
                    "pageInfo": page_info,
                }
            }
        }


class FakeMe:
    online_id = "LibraryOwner"

    def __init__(self):
        self.authenticator = FakeAuthenticator()
        self.title_stats_calls = 0

    def title_stats(self):
        self.title_stats_calls += 1
        return [
            SimpleNamespace(
                title_id="PPSA00001_00",
                name="Started Game",
                category=SimpleNamespace(value="ps5_native_game"),
                play_duration=timedelta(hours=4),
            )
        ]

    def trophy_titles(self):
        return [
            SimpleNamespace(
                title_name="Finished Game",
                title_platform=[SimpleNamespace(value="PS4")],
                progress=100,
                earned_trophies=SimpleNamespace(platinum=0, gold=2, silver=3, bronze=4),
                defined_trophies=SimpleNamespace(platinum=0, gold=2, silver=3, bronze=4),
            )
        ]


def test_advisor_library_pages_matches_status_and_caches(monkeypatch, tmp_path):
    me = FakeMe()
    monkeypatch.setattr(advisor_service, "_client", lambda _token: me)
    cache = FileCache(tmp_path)

    first = advisor_service.get_advisor_library(
        "libraryowner", npsso="token", cache=cache
    )
    second = advisor_service.get_advisor_library(
        "LibraryOwner", npsso="token", cache=cache
    )

    assert first.total_count == 3
    assert first.unplayed_count == 1
    assert first.in_progress_count == 1
    assert first.completed_count == 1
    assert first.games[0].status == "in_progress"
    assert first.games[0].playtime_seconds == 14_400
    assert first.games[1].status == "completed"
    assert first.games[1].source == "ps_plus"
    assert first.games[1].earned_trophies == 9
    assert first.games[1].earned_platinum == 0
    assert first.games[2].status == "unplayed"
    assert first.cache_status == "live"
    assert second.cache_status == "cached"
    assert me.authenticator.calls == 2
    assert me.title_stats_calls == 1


def test_advisor_library_rejects_non_owner(monkeypatch, tmp_path):
    monkeypatch.setattr(advisor_service, "_client", lambda _token: FakeMe())

    with pytest.raises(advisor_service.AdvisorOwnerMismatchError):
        advisor_service.get_advisor_library(
            "AnotherPlayer", npsso="token", cache=FileCache(tmp_path)
        )


def test_advisor_library_uses_valid_cache_before_reauthenticating(monkeypatch, tmp_path):
    cache = FileCache(tmp_path)
    me = FakeMe()
    monkeypatch.setattr(advisor_service, "_client", lambda _token: me)
    advisor_service.get_advisor_library("LibraryOwner", npsso="token", cache=cache)

    def broken_client(_token):
        raise AssertionError("A valid owner cache should not reauthenticate")

    monkeypatch.setattr(advisor_service, "_client", broken_client)
    cached = advisor_service.get_advisor_library(
        "libraryowner", npsso="token", cache=cache
    )

    assert cached.cache_status == "cached"
    assert cached.total_count == 3


def test_advisor_signal_batch_reuses_session(monkeypatch):
    class Session:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

    session = Session()
    monkeypatch.setattr(advisor_service, "create_session", lambda: session)
    calls = []

    def fake_lookup(
        game,
        platform,
        *,
        search_aliases,
        cache_only,
        cache,
        session,
    ):
        assert cache_only is False
        calls.append((game, platform, search_aliases, session))
        return {
            "title": game,
            "platform": platform,
            "game_url": "https://psnprofiles.com/trophies/1-game",
            "owners": 12_345,
            "average_completion": 67.8,
            "platinum_achievers": 5_000,
            "platinum_rate": 40.5,
        }

    monkeypatch.setattr(advisor_service, "get_psnprofiles_trophies", fake_lookup)
    results = advisor_service.get_advisor_signals_batch(
        [
            AdvisorCandidate(
                game="One",
                platform="PS5",
                aliases=["One Alias", "遊戲一"],
            ),
            AdvisorCandidate(game="Two", platform="PS4"),
        ]
    )

    assert len(results) == 2
    assert results[0].signals is not None
    assert results[0].signals.owners == 12_345
    assert calls[0][2] == ["One", "One Alias"]
    assert calls[0][3] is session
    assert calls[1][3] is session


def test_advisor_never_sends_localized_alias_to_psnprofiles_search(monkeypatch):
    class Session:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

    monkeypatch.setattr(advisor_service, "create_session", Session)
    monkeypatch.setattr(advisor_service.settings, "gemini_api_key", None)
    calls = []

    def fake_lookup(game, platform, **kwargs):
        calls.append((game, platform, kwargs["search_aliases"]))
        return None

    monkeypatch.setattr(advisor_service, "get_psnprofiles_trophies", fake_lookup)

    advisor_service.get_advisor_signals_batch(
        [
            AdvisorCandidate(
                game="LittleBigPlanet 3",
                platform="PS4",
                aliases=["小小大星球3"],
            )
        ]
    )

    assert calls == [("LittleBigPlanet 3", "PS4", ["LittleBigPlanet 3"])]


def test_advisor_retries_unmatched_title_once_with_explicit_grounded_alternative(monkeypatch):
    class Session:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

    monkeypatch.setattr(advisor_service, "create_session", Session)
    monkeypatch.setattr(advisor_service.settings, "gemini_api_key", "secret")
    candidate = AdvisorCandidate(game="Wrong Store Name", platform="PS5")
    resolution_calls = []

    def fake_resolve(candidates, **kwargs):
        resolution_calls.append(kwargs)
        if kwargs.get("retry_attempts"):
            return {
                candidate_key(item): TitleResolution(
                    "Corrected Game",
                    source="gemini",
                )
                for item in candidates
            }
        return {
            candidate_key(item): TitleResolution(
                "Wrong Store Name",
                source="source_title",
            )
            for item in candidates
        }

    monkeypatch.setattr(advisor_service, "resolve_advisor_titles", fake_resolve)
    calls = []

    def fake_lookup(game, platform, **kwargs):
        calls.append((game, platform, kwargs["session"]))
        if game == "Wrong Store Name":
            return None
        return {
            "title": game,
            "platform": platform,
            "game_url": "https://psnprofiles.com/trophies/1-corrected-game",
            "owners": 100,
            "average_completion": 50.0,
            "platinum_achievers": 25,
            "platinum_rate": 25.0,
        }

    monkeypatch.setattr(advisor_service, "get_psnprofiles_trophies", fake_lookup)

    result = advisor_service.get_advisor_signals_batch([candidate], retry_title_lookup=True)[0]

    assert result.signals is not None
    assert result.signals.title == "Corrected Game"
    assert [call[0] for call in calls] == ["Wrong Store Name", "Corrected Game"]
    assert len(resolution_calls) == 2
    assert resolution_calls[1]["retry_attempts"] == {
        candidate_key(candidate): "Wrong Store Name"
    }


def test_known_multi_trophy_list_package_analyzes_each_child(monkeypatch):
    class Session:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

    monkeypatch.setattr(advisor_service, "create_session", Session)

    calls = []

    def fake_lookup(game, platform, **_kwargs):
        calls.append((game, platform))
        return {
            "title": game,
            "platform": platform,
            "game_url": f"https://psnprofiles.com/trophies/1-{len(calls)}",
            "owners": 100,
            "average_completion": 50.0,
            "platinum_achievers": 25,
            "platinum_rate": 25.0,
        }

    monkeypatch.setattr(
        advisor_service,
        "get_psnprofiles_trophies",
        fake_lookup,
    )

    result = advisor_service.get_advisor_signals_batch(
        [AdvisorCandidate(game="BioShock: The Collection", platform="PS4")]
    )[0]

    assert result.signals is None
    assert result.error is None
    assert result.bundle is not None
    assert result.bundle.source == "curated"
    assert result.bundle.complete is True
    assert [child.game for child in result.bundle.children] == [
        "BioShock Remastered",
        "BioShock 2 Remastered",
        "BioShock Infinite",
    ]
    assert calls == [
        ("BioShock Remastered", "PS4"),
        ("BioShock 2 Remastered", "PS4"),
        ("BioShock Infinite", "PS4"),
    ]


def test_cached_advisor_batch_never_creates_browser(monkeypatch, tmp_path):
    def unexpected_session():
        raise AssertionError("cached-only hydration must not create a browser")

    monkeypatch.setattr(advisor_service, "create_session", unexpected_session)

    results = advisor_service.get_advisor_signals_batch(
        [AdvisorCandidate(game="Uncached Game", platform="PS5")],
        cache=FileCache(tmp_path),
        cache_only=True,
    )

    assert len(results) == 1
    assert results[0].signals is None
    assert results[0].error is None


def test_cached_unknown_collection_waits_for_explicit_grounded_analysis(
    monkeypatch,
    tmp_path,
):
    def unexpected_session():
        raise AssertionError("cached-only hydration must not create a browser")

    def unexpected_lookup(*_args, **_kwargs):
        raise AssertionError("an unresolved collection must not use a parent trophy list")

    monkeypatch.setattr(advisor_service, "create_session", unexpected_session)
    monkeypatch.setattr(
        advisor_service,
        "get_psnprofiles_trophies",
        unexpected_lookup,
    )

    result = advisor_service.get_advisor_signals_batch(
        [AdvisorCandidate(game="Unknown Game Collection", platform="PS5")],
        cache=FileCache(tmp_path),
        cache_only=True,
    )[0]

    assert result.signals is None
    assert result.bundle is None
    assert result.error is not None
    assert result.retryable is True


@pytest.mark.parametrize(
    "name",
    [
        "Game Demo",
        "Game Trial Version",
        "Game Open Beta",
        "Call of Duty: Black Ops 4 Private Beta",
        "PUBG - Public Test Server",
        "Game Test Server",
        "Game PTS",
        "Monster Hunter: World Beta",
        "《天命2》Beta測試",
        "遊戲 試玩版",
        "遊戲 體驗版",
        "ゲーム 体験版",
    ],
)
def test_trial_and_demo_titles_are_excluded(name):
    assert advisor_service._is_trial_game(_raw_game("PPSA99999_00", name, "PS5"))


def test_full_game_with_trials_in_title_is_not_excluded():
    assert not advisor_service._is_trial_game(
        _raw_game("PPSA99998_00", "Trials of Mana", "PS5")
    )


@pytest.mark.parametrize("name", ["Test Drive Unlimited", "Server Room Simulator"])
def test_regular_titles_with_test_or_server_words_are_not_excluded(name):
    assert not advisor_service._is_trial_game(
        _raw_game("PPSA99997_00", name, "PS5")
    )


def test_trophyless_teaser_is_excluded_as_trial_content():
    assert advisor_service._is_trial_game(
        _raw_game(
            "CUSA99996_00",
            "Resident Evil 7 Teaser: Beginning Hour",
            "PS4",
        )
    )


@pytest.mark.parametrize(
    "name",
    [
        "IGN",
        "Spotify",
        "Netflix",
        "Twitch",
        "BRAVIA TV Player",
        "Media Player",
        "媒體播放器",
        "YouTube",
    ],
)
def test_known_media_apps_are_excluded_from_game_advisor(name):
    assert advisor_service._is_non_game_content(
        _raw_game("CUSA99995_00", name, "PS4")
    )


def test_media_app_product_id_is_excluded_even_with_unknown_localized_name():
    raw = _raw_game("CUSA99994_00", "影音服務", "PS4")
    raw["productId"] = "HA0001-CUSA03878_00-BRAVIATVPLAYER01"

    assert advisor_service._is_non_game_content(raw)


def test_build_games_removes_trials_before_returning_library():
    games, excluded_trials, excluded_content, excluded_platinums = advisor_service._build_games(
        [
            _raw_game("PPSA10000_00", "Real Game", "PS5"),
            _raw_game("PPSA10001_00", "Real Game Demo", "PS5"),
        ],
        [],
        [],
    )

    assert [game.name for game in games] == ["Real Game"]
    assert excluded_trials == 1
    assert excluded_content == 0
    assert excluded_platinums == 0


def test_build_games_removes_all_console_versions_after_earning_platinum():
    platinum = SimpleNamespace(
        title_name="Stacked Game",
        title_platform=[SimpleNamespace(value="PS5")],
        progress=70,
        earned_trophies=SimpleNamespace(platinum=1, gold=2, silver=3, bronze=4),
        defined_trophies=SimpleNamespace(platinum=1, gold=2, silver=3, bronze=4),
    )

    games, excluded_trials, excluded_content, excluded_platinums = advisor_service._build_games(
        [
            _raw_game("PPSA20000_00", "Stacked Game", "PS5"),
            _raw_game("CUSA20000_00", "Stacked Game", "PS4"),
        ],
        [],
        [platinum],
    )

    assert games == []
    assert excluded_trials == 0
    assert excluded_content == 0
    assert excluded_platinums == 2


def test_build_games_uses_title_id_playtime_name_to_match_localized_library_title():
    platinum = SimpleNamespace(
        title_name="Horizon Forbidden West",
        title_platform=[SimpleNamespace(value="PS5")],
        progress=100,
        earned_trophies=SimpleNamespace(platinum=1, gold=1, silver=1, bronze=1),
        defined_trophies=SimpleNamespace(platinum=1, gold=1, silver=1, bronze=1),
    )

    games, excluded_trials, excluded_content, excluded_platinums = advisor_service._build_games(
        [_raw_game("PPSA17903_00", "地平線 西域禁地", "PS5")],
        [
            {
                "title_id": "PPSA17903_00",
                "name": "Horizon Forbidden West",
                "platform": "PS5",
                "seconds": 3_600,
            }
        ],
        [platinum],
    )

    assert games == []
    assert excluded_trials == 0
    assert excluded_content == 0
    assert excluded_platinums == 1


def test_build_games_removes_fuzzy_same_platform_platinum_match():
    platinum = SimpleNamespace(
        title_name="Game Name: Definitive Edition",
        title_platform=[SimpleNamespace(value="PS5")],
        progress=100,
        earned_trophies=SimpleNamespace(platinum=1, gold=1, silver=1, bronze=1),
        defined_trophies=SimpleNamespace(platinum=1, gold=1, silver=1, bronze=1),
    )

    games, excluded_trials, excluded_content, excluded_platinums = advisor_service._build_games(
        [_raw_game("PPSA30000_00", "Game Name", "PS5")],
        [],
        [platinum],
    )

    assert games == []
    assert excluded_trials == 0
    assert excluded_content == 0
    assert excluded_platinums == 1


@pytest.mark.parametrize(
    "name",
    [
        "Horizon Forbidden West Bonus Content",
        "地平線 西域禁地 數位豪華內容",
        "Horizon Forbidden West ボーナスコンテンツ",
        "浪人崛起 - 特典內容",
        "SILENT HILL 2 - 額外內容",
        "緋紅結繫 數位美術集＆數位原聲帶",
        "暗喻幻想：ReFantazio 數位豪華美術書",
        "暗喻幻想：ReFantazio 數位特別原聲帶",
        "ATLUS品牌35th 數位歷史書",
        "ATLUS品牌35th 數位永恆精選",
        'Premium Musical Notes “NieR in Concert: "A Deprival in White, A Revival in Black"”',
    ],
)
def test_build_games_removes_non_game_content_entitlements(name):
    games, excluded_trials, excluded_content, excluded_platinums = advisor_service._build_games(
        [_raw_game("PPSA03780_00", name, "PS5")],
        [],
        [],
    )

    assert games == []
    assert excluded_trials == 0
    assert excluded_content == 1
    assert excluded_platinums == 0


def test_digital_deluxe_edition_game_is_not_treated_as_bonus_content():
    assert not advisor_service._is_non_game_content(
        _raw_game("PPSA40000_00", "Game Digital Deluxe Edition", "PS5")
    )


def test_cross_platform_games_merge_and_continue_the_started_edition():
    ps4 = _raw_game("CUSA50000_00", "Cross Gen Game", "PS4")
    ps5 = _raw_game("PPSA50000_00", "Cross Gen Game", "PS5")
    ps4["productId"] = ps5["productId"] = "cross-gen-bundle"
    games, _, _, _ = advisor_service._build_games(
        [ps4, ps5],
        [
            {
                "title_id": "CUSA50000_00",
                "name": "Cross Gen Game",
                "platform": "PS4",
                "seconds": 7_200,
            }
        ],
        [],
    )

    merged, merged_count = advisor_service._merge_cross_platform_games(games)

    assert len(merged) == 1
    assert merged_count == 1
    assert merged[0].platform == "PS4"
    assert merged[0].available_platforms == ["PS5", "PS4"]
    assert merged[0].playtime_seconds == 7_200


def test_cross_platform_unplayed_game_prefers_ps5():
    ps4 = _raw_game("CUSA50001_00", "Another Cross Gen Game", "PS4")
    ps5 = _raw_game("PPSA50001_00", "Another Cross Gen Game", "PS5")
    ps4["productId"] = ps5["productId"] = "another-cross-gen-bundle"
    games, _, _, _ = advisor_service._build_games([ps4, ps5], [], [])

    merged, merged_count = advisor_service._merge_cross_platform_games(games)

    assert len(merged) == 1
    assert merged_count == 1
    assert merged[0].platform == "PS5"
    assert merged[0].available_platforms == ["PS5", "PS4"]
    assert merged[0].ps4_to_ps5_autopop == "unknown"
    assert merged[0].autopop_note


def test_ps4_platinum_with_confirmed_partial_autopop_keeps_ps5_opportunity():
    ps4_platinum = SimpleNamespace(
        title_name="Nioh 2",
        title_platform=[SimpleNamespace(value="PS4")],
        progress=100,
        earned_trophies=SimpleNamespace(platinum=1, gold=2, silver=3, bronze=4),
        defined_trophies=SimpleNamespace(platinum=1, gold=2, silver=3, bronze=4),
    )

    games, _, _, excluded_platinums = advisor_service._build_games(
        [_raw_game("PPSA02462_00", "仁王２ Remastered", "PS5")],
        [
            {
                "title_id": "PPSA02462_00",
                "name": "Nioh 2",
                "platform": "PS5",
                "seconds": 3_600,
            }
        ],
        [ps4_platinum],
    )

    assert excluded_platinums == 0
    assert len(games) == 1
    assert games[0].platform == "PS5"
    assert games[0].available_platforms == ["PS5", "PS4"]
    assert games[0].ps4_platinum_earned is True
    assert games[0].ps4_to_ps5_autopop == "partial"
    assert games[0].autopop_source_url


def test_ps4_platinum_without_autopop_stays_excluded():
    ps4_platinum = SimpleNamespace(
        title_name="Tunic",
        title_platform=[SimpleNamespace(value="PS4")],
        progress=100,
        earned_trophies=SimpleNamespace(platinum=1, gold=2, silver=3, bronze=4),
        defined_trophies=SimpleNamespace(platinum=1, gold=2, silver=3, bronze=4),
    )

    games, _, _, excluded_platinums = advisor_service._build_games(
        [_raw_game("PPSA99991_00", "Tunic", "PS5")],
        [],
        [ps4_platinum],
    )

    assert games == []
    assert excluded_platinums == 1


def test_ps5_platinum_is_excluded_even_when_game_supports_full_autopop():
    ps5_platinum = SimpleNamespace(
        title_name="Resident Evil 4",
        title_platform=[SimpleNamespace(value="PS5")],
        progress=100,
        earned_trophies=SimpleNamespace(platinum=1, gold=2, silver=3, bronze=4),
        defined_trophies=SimpleNamespace(platinum=1, gold=2, silver=3, bronze=4),
    )

    games, _, _, excluded_platinums = advisor_service._build_games(
        [_raw_game("PPSA99992_00", "Resident Evil 4", "PS5")],
        [],
        [ps5_platinum],
    )

    assert games == []
    assert excluded_platinums == 1


def test_known_cross_gen_game_carries_autopop_status_to_merged_card():
    ps4 = _raw_game("CUSA99993_00", "Tales of Arise", "PS4")
    ps5 = _raw_game("PPSA99993_00", "Tales of Arise", "PS5")
    ps4["productId"] = ps5["productId"] = "tales-cross-gen"

    games, _, _, _ = advisor_service._build_games([ps4, ps5], [], [])
    merged, _ = advisor_service._merge_cross_platform_games(games)

    assert len(merged) == 1
    assert merged[0].available_platforms == ["PS5", "PS4"]
    assert merged[0].ps4_to_ps5_autopop == "full"
    assert merged[0].autopop_source_url
