import json

from app.core.cache import FileCache
from app.models import AdvisorCandidate
from app.services import gemini_title_service


class FakeGeminiResponse:
    def raise_for_status(self):
        return None

    def json(self):
        content = {
            "games": [
                {
                    "id": "0",
                    "english_title": "WUCHANG: Fallen Feathers",
                    "is_trial": False,
                }
            ]
        }
        return {
            "candidates": [
                {"content": {"parts": [{"text": json.dumps(content)}]}}
            ]
        }


def test_gemini_resolves_localized_title_and_caches(monkeypatch, tmp_path):
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return FakeGeminiResponse()

    monkeypatch.setattr(gemini_title_service.settings, "gemini_api_key", "secret")
    monkeypatch.setattr(
        gemini_title_service.settings,
        "gemini_grounding_model",
        "gemini-2.5-flash",
    )
    monkeypatch.setattr(gemini_title_service.requests, "post", fake_post)
    candidate = AdvisorCandidate(
        game="明末：淵虛之羽",
        platform="PS5",
        title_id="PPSA00001_00",
    )
    cache = FileCache(tmp_path)

    first = gemini_title_service.resolve_advisor_titles([candidate], cache=cache)
    second = gemini_title_service.resolve_advisor_titles([candidate], cache=cache)
    resolution = first[gemini_title_service.candidate_key(candidate)]

    assert resolution.search_title == "WUCHANG Fallen Feathers"
    assert resolution.source == "gemini"
    assert second == first
    assert len(calls) == 1
    assert calls[0][1]["headers"]["x-goog-api-key"] == "secret"
    assert calls[0][0].endswith("gemini-2.5-flash:generateContent")
    assert calls[0][1]["json"]["tools"] == [{"google_search": {}}]
    assert "generationConfig" not in calls[0][1]["json"]


def test_missing_key_uses_existing_english_title(monkeypatch, tmp_path):
    monkeypatch.setattr(gemini_title_service.settings, "gemini_api_key", None)
    candidate = AdvisorCandidate(game="KNACK™", platform="PS4")

    resolutions = gemini_title_service.resolve_advisor_titles(
        [candidate],
        cache=FileCache(tmp_path),
    )

    assert resolutions[gemini_title_service.candidate_key(candidate)].search_title == (
        "KNACK"
    )


def test_configured_gemini_is_not_called_for_english_title(monkeypatch, tmp_path):
    def unexpected_post(*_args, **_kwargs):
        raise AssertionError("English titles must not consume Gemini quota")

    monkeypatch.setattr(gemini_title_service.settings, "gemini_api_key", "secret")
    monkeypatch.setattr(gemini_title_service.requests, "post", unexpected_post)
    candidate = AdvisorCandidate(game="KNACK™", platform="PS4")

    resolutions = gemini_title_service.resolve_advisor_titles(
        [candidate],
        cache=FileCache(tmp_path),
    )

    assert resolutions[gemini_title_service.candidate_key(candidate)].search_title == (
        "KNACK"
    )


def test_known_psnprofiles_search_spelling_uses_deterministic_override(
    monkeypatch,
    tmp_path,
):
    def unexpected_post(*_args, **_kwargs):
        raise AssertionError("A deterministic English alias must not use Gemini")

    monkeypatch.setattr(gemini_title_service.settings, "gemini_api_key", "secret")
    monkeypatch.setattr(gemini_title_service.requests, "post", unexpected_post)

    candidates = [
        AdvisorCandidate(game="DIRT5", platform="PS5"),
        AdvisorCandidate(game="ABZU", platform="PS4"),
        AdvisorCandidate(game="Evil Dead: The Game", platform="PS5"),
        AdvisorCandidate(game="Godfall: Challenger Edition", platform="PS5"),
        AdvisorCandidate(game="LittleBigPlanet™3", platform="PS4"),
        AdvisorCandidate(game="RESIDENT EVIL UMBRELLA CORPS", platform="PS4"),
    ]
    resolutions = gemini_title_service.resolve_advisor_titles(
        candidates,
        cache=FileCache(tmp_path),
    )

    assert [
        resolutions[gemini_title_service.candidate_key(candidate)].search_title
        for candidate in candidates
    ] == [
        "DIRT 5",
        "ABZÛ",
        "Evil Dead",
        "Godfall",
        "LittleBigPlanet 3",
        "Umbrella Corps",
    ]


def test_localized_collection_defers_to_single_grounded_bundle_call(
    monkeypatch,
    tmp_path,
):
    def unexpected_post(*_args, **_kwargs):
        raise AssertionError("The title resolver must not spend quota on a bundle parent")

    monkeypatch.setattr(gemini_title_service.settings, "gemini_api_key", "secret")
    monkeypatch.setattr(gemini_title_service.requests, "post", unexpected_post)
    candidate = AdvisorCandidate(game="範例遊戲合集", platform="PS5")

    resolution = gemini_title_service.resolve_advisor_titles(
        [candidate],
        cache=FileCache(tmp_path),
    )[gemini_title_service.candidate_key(candidate)]

    assert resolution.search_title == "範例遊戲合集"
    assert resolution.source == "source_title"


def test_transient_503_is_retried_once(monkeypatch, tmp_path):
    calls = []

    class UnavailableResponse:
        status_code = 503

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return UnavailableResponse() if len(calls) == 1 else FakeGeminiResponse()

    monkeypatch.setattr(gemini_title_service.settings, "gemini_api_key", "secret")
    monkeypatch.setattr(
        gemini_title_service.settings,
        "gemini_grounding_model",
        "gemini-2.5-flash",
    )
    monkeypatch.setattr(gemini_title_service.requests, "post", fake_post)
    monkeypatch.setattr(gemini_title_service.time, "sleep", lambda _seconds: None)
    candidate = AdvisorCandidate(game="明末：淵虛之羽", platform="PS5")

    resolution = gemini_title_service.resolve_advisor_titles(
        [candidate],
        cache=FileCache(tmp_path),
    )[gemini_title_service.candidate_key(candidate)]

    assert resolution.search_title == "WUCHANG Fallen Feathers"
    assert len(calls) == 2


def test_grounded_titles_are_split_into_independently_cached_batches(
    monkeypatch,
    tmp_path,
):
    request_sizes = []

    class BatchResponse:
        status_code = 200

        def __init__(self, games):
            self.games = games

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "candidates": [
                    {
                        "finishReason": "STOP",
                        "content": {
                            "parts": [
                                {
                                    "text": json.dumps(
                                        {"games": self.games},
                                        ensure_ascii=False,
                                    )
                                }
                            ]
                        },
                    }
                ]
            }

    def fake_post(_url, **kwargs):
        prompt = kwargs["json"]["contents"][0]["parts"][0]["text"]
        records = json.loads(prompt.split("Games:\n", 1)[1])
        request_sizes.append(len(records))
        return BatchResponse(
            [
                {
                    "id": record["id"],
                    "english_title": f"Resolved Game {record['id']}",
                    "is_trial": False,
                }
                for record in records
            ]
        )

    monkeypatch.setattr(gemini_title_service.settings, "gemini_api_key", "secret")
    monkeypatch.setattr(gemini_title_service.requests, "post", fake_post)
    candidates = [
        AdvisorCandidate(
            game=f"測試遊戲 {index}",
            platform="PS5",
            title_id=f"PPSA{index:05d}_00",
        )
        for index in range(13)
    ]
    cache = FileCache(tmp_path)

    first = gemini_title_service.resolve_advisor_titles(candidates, cache=cache)
    second = gemini_title_service.resolve_advisor_titles(candidates, cache=cache)

    assert request_sizes == [12, 1]
    assert second == first
    assert all(resolution.source == "gemini" for resolution in first.values())


def test_retry_grounding_includes_previous_title_and_requires_a_new_title(
    monkeypatch,
    tmp_path,
):
    requests_seen = []

    class RetryResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": json.dumps(
                                        {
                                            "games": [
                                                {
                                                    "id": "0",
                                                    "english_title": "Corrected Game",
                                                    "is_trial": False,
                                                }
                                            ]
                                        }
                                    )
                                }
                            ]
                        }
                    }
                ]
            }

    def fake_post(_url, **kwargs):
        prompt = kwargs["json"]["contents"][0]["parts"][0]["text"]
        requests_seen.append(json.loads(prompt.split("Games:\n", 1)[1]))
        return RetryResponse()

    monkeypatch.setattr(gemini_title_service.settings, "gemini_api_key", "secret")
    monkeypatch.setattr(gemini_title_service.requests, "post", fake_post)
    candidate = AdvisorCandidate(game="錯誤名稱", platform="PS5")
    cache = FileCache(tmp_path)

    resolution = gemini_title_service.resolve_advisor_titles(
        [candidate],
        cache=cache,
        retry_attempts={
            gemini_title_service.candidate_key(candidate): "Wrong Store Name"
        },
    )[gemini_title_service.candidate_key(candidate)]

    assert resolution.search_title == "Corrected Game"
    assert resolution.source == "gemini"
    assert requests_seen == [
        [
            {
                "id": "0",
                "source_names": ["錯誤名稱"],
                "platform": "PS5",
                "title_id": None,
                "product_id": None,
                "previous_search_title": "Wrong Store Name",
            }
        ]
    ]


def test_cache_only_can_use_legacy_title_as_existing_signal_index(
    monkeypatch,
    tmp_path,
):
    def unexpected_post(*_args, **_kwargs):
        raise AssertionError("cache-only restoration must never call Gemini")

    monkeypatch.setattr(gemini_title_service.settings, "gemini_api_key", "secret")
    monkeypatch.setattr(gemini_title_service.requests, "post", unexpected_post)
    candidate = AdvisorCandidate(
        game="明末：淵虛之羽",
        platform="PS5",
        title_id="PPSA00001_00",
    )
    cache = FileCache(tmp_path)
    cache.save(
        gemini_title_service._legacy_cache_key(candidate),
        {
            "english_title": "WUCHANG Fallen Feathers",
            "is_trial": False,
        },
    )

    resolution = gemini_title_service.resolve_advisor_titles(
        [candidate],
        cache=cache,
        allow_api=False,
    )[gemini_title_service.candidate_key(candidate)]

    assert resolution.search_title == "WUCHANG Fallen Feathers"
    assert resolution.source == "legacy_cache"
    assert cache.load(gemini_title_service._cache_key(candidate), 60) is None


def test_live_resolution_does_not_reuse_legacy_title(monkeypatch, tmp_path):
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return FakeGeminiResponse()

    monkeypatch.setattr(gemini_title_service.settings, "gemini_api_key", "secret")
    monkeypatch.setattr(gemini_title_service.requests, "post", fake_post)
    candidate = AdvisorCandidate(
        game="明末：淵虛之羽",
        platform="PS5",
        title_id="PPSA00001_00",
    )
    cache = FileCache(tmp_path)
    cache.save(
        gemini_title_service._legacy_cache_key(candidate),
        {"english_title": "Incorrect Legacy Title", "is_trial": False},
    )

    resolution = gemini_title_service.resolve_advisor_titles(
        [candidate],
        cache=cache,
        allow_api=True,
    )[gemini_title_service.candidate_key(candidate)]

    assert resolution.search_title == "WUCHANG Fallen Feathers"
    assert resolution.source == "gemini"
    assert len(calls) == 1


def test_curated_override_supersedes_incorrect_grounded_cache(monkeypatch, tmp_path):
    def unexpected_post(*_args, **_kwargs):
        raise AssertionError("a curated correction must not call Gemini")

    monkeypatch.setattr(gemini_title_service.settings, "gemini_api_key", "secret")
    monkeypatch.setattr(gemini_title_service.requests, "post", unexpected_post)
    candidate = AdvisorCandidate(
        game="異環",
        platform="PS5",
        title_id="PPSA00002_00",
    )
    cache = FileCache(tmp_path)
    cache.save(
        gemini_title_service._cache_key(candidate),
        {"english_title": "Project The Perceiver", "is_trial": False},
    )

    resolution = gemini_title_service.resolve_advisor_titles(
        [candidate],
        cache=cache,
        allow_api=False,
    )[gemini_title_service.candidate_key(candidate)]

    assert resolution.search_title == "Neverness to Everness"
    assert resolution.source == "override"
