import json

from app.core.cache import FileCache
from app.models import AdvisorCandidate
from app.services import gemini_bundle_service
from app.services.gemini_title_service import candidate_key


class FakeGeminiResponse:
    def raise_for_status(self):
        return None

    def json(self):
        content = {
            "collections": [
                {
                    "id": "0",
                    "separate_trophy_lists": True,
                    "children": [
                        {"english_title": "Game One", "platform": "PS5"},
                        {"english_title": "Game Two", "platform": "PS4"},
                    ],
                }
            ]
        }
        return {
            "candidates": [
                {
                    "content": {"parts": [{"text": json.dumps(content)}]},
                    "groundingMetadata": {
                        "groundingChunks": [
                            {"web": {"uri": "https://example.com/source"}}
                        ]
                    },
                }
            ]
        }


def test_unknown_bundle_uses_flash_grounding_once_and_caches(monkeypatch, tmp_path):
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return FakeGeminiResponse()

    monkeypatch.setattr(gemini_bundle_service.settings, "gemini_api_key", "secret")
    monkeypatch.setattr(
        gemini_bundle_service.settings,
        "gemini_grounding_model",
        "gemini-2.5-flash",
    )
    monkeypatch.setattr(gemini_bundle_service.requests, "post", fake_post)
    candidate = AdvisorCandidate(
        game="Example Game Collection",
        platform="PS5",
        product_id="example-collection",
    )
    key = candidate_key(candidate)
    cache = FileCache(tmp_path)

    first = gemini_bundle_service.resolve_advisor_bundles(
        [candidate],
        {key: candidate.game},
        cache=cache,
        allow_api=True,
    )
    second = gemini_bundle_service.resolve_advisor_bundles(
        [candidate],
        {key: candidate.game},
        cache=cache,
        allow_api=True,
    )

    assert len(calls) == 1
    assert calls[0][0].endswith("gemini-2.5-flash:generateContent")
    assert calls[0][1]["headers"]["x-goog-api-key"] == "secret"
    assert calls[0][1]["json"]["tools"] == [{"google_search": {}}]
    assert [child.game for child in first[key].children] == ["Game One", "Game Two"]
    assert first[key].source_urls == ("https://example.com/source",)
    assert second == first


def test_known_bundle_does_not_consume_gemini_quota(monkeypatch, tmp_path):
    def unexpected_post(*_args, **_kwargs):
        raise AssertionError("Curated bundles must not call Gemini")

    monkeypatch.setattr(gemini_bundle_service.settings, "gemini_api_key", "secret")
    monkeypatch.setattr(gemini_bundle_service.requests, "post", unexpected_post)
    candidate = AdvisorCandidate(game="BioShock: The Collection", platform="PS4")
    key = candidate_key(candidate)

    result = gemini_bundle_service.resolve_advisor_bundles(
        [candidate],
        {key: candidate.game},
        cache=FileCache(tmp_path),
        allow_api=True,
    )[key]

    assert result.source == "curated"
    assert len(result.children) == 3


def test_nathan_drake_collection_uses_three_curated_trophy_lists(
    monkeypatch,
    tmp_path,
):
    def unexpected_post(*_args, **_kwargs):
        raise AssertionError("The known collection must not call Gemini")

    monkeypatch.setattr(gemini_bundle_service.settings, "gemini_api_key", "secret")
    monkeypatch.setattr(gemini_bundle_service.requests, "post", unexpected_post)
    candidate = AdvisorCandidate(
        game="Uncharted: The Nathan Drake Collection™",
        platform="PS4",
    )
    key = candidate_key(candidate)

    result = gemini_bundle_service.resolve_advisor_bundles(
        [candidate],
        {key: "Uncharted The Nathan Drake Collection"},
        cache=FileCache(tmp_path),
        allow_api=True,
    )[key]

    assert [child.game for child in result.children] == [
        "Uncharted: Drake's Fortune Remastered",
        "Uncharted 2: Among Thieves Remastered",
        "Uncharted 3: Drake's Deception Remastered",
    ]


def test_dark_pictures_anthology_title_is_not_treated_as_a_collection(
    monkeypatch,
    tmp_path,
):
    def unexpected_post(*_args, **_kwargs):
        raise AssertionError("A standalone Dark Pictures game must not use grounding")

    monkeypatch.setattr(gemini_bundle_service.settings, "gemini_api_key", "secret")
    monkeypatch.setattr(gemini_bundle_service.requests, "post", unexpected_post)
    candidate = AdvisorCandidate(
        game="The Dark Pictures Anthology: House of Ashes",
        platform="PS5",
    )
    key = candidate_key(candidate)

    result = gemini_bundle_service.resolve_advisor_bundles(
        [candidate],
        {key: "The Dark Pictures Anthology House of Ashes"},
        cache=FileCache(tmp_path),
        allow_api=True,
    )

    assert result == {}
