"""Resolve localized PlayStation titles before searching PSNProfiles."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass

import requests

from app.config import settings
from app.core.cache import FileCache
from app.models import AdvisorCandidate
from app.services.psnprofiles_guide_service import psnprofiles_search_query

logger = logging.getLogger(__name__)

_RESOLUTION_TTL = 180 * 24 * 3600
_CJK = re.compile(r"[\u3400-\u9fff\uf900-\ufaff]")
_LATIN = re.compile(r"[A-Za-z]{2}")
_BUNDLE_MARKER = re.compile(
    r"\b(collection|bundle|anthology|trilogy|compilation)\b|"
    r"合集|合輯|套裝|合輯版|コレクション|トリロジー",
    flags=re.IGNORECASE,
)
_PSNPROFILES_TITLE_OVERRIDES = {
    "abzu": "ABZÛ",
    "dirt5": "DIRT 5",
    "evil dead the game": "Evil Dead",
    "godfall challenger edition": "Godfall",
    "littlebigplanet3": "LittleBigPlanet 3",
    "resident evil umbrella corps": "Umbrella Corps",
    "異環": "Neverness to Everness",
}
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
_TITLE_GROUNDING_BATCH_SIZE = 12
_LEGACY_TITLE_MODEL = "gemini-3.7-flash"


@dataclass(frozen=True)
class TitleResolution:
    search_title: str
    is_trial: bool = False
    source: str = "source_title"
    error: str | None = None


def candidate_key(candidate: AdvisorCandidate) -> str:
    return f"{candidate.game.strip().casefold()}\0{candidate.platform or 'UNKNOWN'}"


def is_english_search_title(title: str) -> bool:
    return bool(_LATIN.search(title)) and not _CJK.search(title)


def _source_title_override(title: str) -> str:
    return _PSNPROFILES_TITLE_OVERRIDES.get(title.casefold(), title)


def _cache_key(candidate: AdvisorCandidate) -> str:
    seed = "\0".join(
        (
            settings.gemini_grounding_model,
            candidate.title_id or "",
            candidate.product_id or "",
            candidate.platform or "UNKNOWN",
            candidate.game,
            *candidate.aliases,
        )
    )
    digest = hashlib.sha256(seed.casefold().encode("utf-8")).hexdigest()
    return f"gemini_grounded_psnprofiles_title_v2/{digest}"


def _legacy_cache_key(candidate: AdvisorCandidate) -> str:
    """Locate pre-grounding titles only for validated cache restoration."""
    seed = "\0".join(
        (
            _LEGACY_TITLE_MODEL,
            candidate.title_id or "",
            candidate.product_id or "",
            candidate.platform or "UNKNOWN",
            candidate.game,
            *candidate.aliases,
        )
    )
    digest = hashlib.sha256(seed.casefold().encode("utf-8")).hexdigest()
    return f"gemini_psnprofiles_title_v1/{digest}"


def _response_text(payload: dict) -> str:
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        prompt_feedback = payload.get("promptFeedback") or {}
        block_reason = prompt_feedback.get("blockReason") or "none"
        raise ValueError(
            f"Gemini did not return a candidate (block_reason={block_reason})"
        )
    content = candidates[0].get("content") or {}
    parts = content.get("parts") or []
    text = "".join(
        str(part.get("text") or "")
        for part in parts
        if isinstance(part, dict)
    ).strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I)
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    if not text:
        finish_reason = candidates[0].get("finishReason") or "unknown"
        raise ValueError(
            f"Gemini returned an empty response (finish_reason={finish_reason})"
        )
    return text


def _request_resolutions(candidates: list[AdvisorCandidate]) -> dict[str, dict]:
    records = [
        {
            "id": str(index),
            "source_names": [candidate.game, *candidate.aliases],
            "platform": candidate.platform,
            "title_id": candidate.title_id,
            "product_id": candidate.product_id,
        }
        for index, candidate in enumerate(candidates)
    ]
    prompt = (
        "Use Google Search to resolve each PlayStation game to its canonical "
        "official English title and verify that the result is suitable as a "
        "PSNProfiles game-search query. Prefer official PlayStation/publisher "
        "sources and PSNProfiles evidence over literal translation. "
        "The title must be short and suitable as a PSNProfiles game-search query: "
        "remove trademark symbols, platform suffixes, bundle labels, edition/store "
        "marketing text, and localized title text. Do not invent a different game. "
        "Also classify demos, trials, betas, playtests, network tests, and time-limited "
        "trial versions as is_trial=true. Full retail games whose story contains the "
        "word trial are not trials. Preserve every input id exactly. Return JSON only "
        "with this exact shape: {\"games\":[{\"id\":\"0\","
        "\"english_title\":\"Canonical English Title\",\"is_trial\":false}]}. "
        "Include one object for every input id and no Markdown fences.\n\n"
        f"Games:\n{json.dumps(records, ensure_ascii=False)}"
    )
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_grounding_model}:generateContent"
    )
    request_kwargs = {
        "headers": {
            "Content-Type": "application/json",
            "x-goog-api-key": settings.gemini_api_key or "",
        },
        "json": {
            "contents": [{"parts": [{"text": prompt}]}],
            # Gemini 2.5 supports both capabilities, but the legacy
            # generateContent API does not guarantee schema-constrained output
            # when a built-in tool is active. Ask for JSON in the prompt and
            # parse it defensively instead.
            "tools": [{"google_search": {}}],
        },
        "timeout": settings.gemini_timeout,
    }
    logger.info(
        "Gemini grounded title lookup start model=%s count=%d",
        settings.gemini_grounding_model,
        len(candidates),
    )
    response = None
    for attempt in range(2):
        response = requests.post(url, **request_kwargs)
        status_code = int(getattr(response, "status_code", 200))
        if status_code not in _RETRYABLE_STATUS_CODES or attempt == 1:
            break
        logger.warning(
            "Gemini title resolution transient HTTP %d; retrying once model=%s count=%d",
            status_code,
            settings.gemini_grounding_model,
            len(candidates),
        )
        time.sleep(1)
    if response is None:
        raise RuntimeError("Gemini request did not produce a response")
    response.raise_for_status()
    parsed = json.loads(_response_text(response.json()))
    games = parsed.get("games")
    if not isinstance(games, list):
        raise ValueError("Gemini response did not contain games")
    resolved = {
        str(item.get("id")): item
        for item in games
        if isinstance(item, dict) and item.get("id") is not None
    }
    logger.info(
        "Gemini grounded title lookup complete model=%s requested=%d returned=%d",
        settings.gemini_grounding_model,
        len(candidates),
        len(resolved),
    )
    return resolved


def resolve_advisor_titles(
    candidates: list[AdvisorCandidate],
    *,
    cache: FileCache | None = None,
    allow_api: bool = True,
) -> dict[str, TitleResolution]:
    """Resolve a batch once, returning safe local fallbacks on API failure."""
    cache = cache or FileCache(settings.cache_dir)
    resolved: dict[str, TitleResolution] = {}
    missing: list[AdvisorCandidate] = []

    for candidate in candidates:
        source_fallback = psnprofiles_search_query(candidate.game) or candidate.game
        fallback = _source_title_override(source_fallback)
        # Curated corrections are stronger than previous model output and must
        # immediately supersede a bad cached resolution.
        if fallback != source_fallback:
            resolved[candidate_key(candidate)] = TitleResolution(
                fallback,
                source="override",
            )
            continue
        # A grounded bundle lookup can resolve both the localized package name
        # and all contained games in one request. Do not spend a second Gemini
        # call translating the parent package first.
        if any(
            _BUNDLE_MARKER.search(name or "") is not None
            for name in [candidate.game, *candidate.aliases]
        ):
            resolved[candidate_key(candidate)] = TitleResolution(fallback)
            continue
        # English/source-Latin titles only need deterministic cleanup (™, platform
        # suffixes, whitespace). Reserve the limited Gemini quota for localized
        # titles that actually need resolution.
        if is_english_search_title(fallback) or not settings.gemini_api_key:
            resolved[candidate_key(candidate)] = TitleResolution(fallback)
            continue
        cached = cache.load(_cache_key(candidate), _RESOLUTION_TTL)
        cached_source = "gemini"
        # A page reload asks for cache-only Advisor signals. In that path only,
        # reuse the old title as an index into an already-scraped PSNProfiles
        # result. The trophy cache performs its current safe title/platform
        # validation, and this legacy value is never used for a new web search or
        # promoted into the grounded cache namespace.
        if cached is None and not allow_api:
            cached = cache.load(_legacy_cache_key(candidate), _RESOLUTION_TTL)
            cached_source = "legacy_cache"
        if cached is None:
            missing.append(candidate)
            continue
        title = psnprofiles_search_query(str(cached.get("english_title") or ""))
        resolved[candidate_key(candidate)] = TitleResolution(
            search_title=title or fallback,
            is_trial=bool(cached.get("is_trial")),
            source=cached_source if title else "source_title",
        )

    # Search grounding is more reliable with a bounded number of unrelated game
    # lookups per prompt. Each successful slice is cached immediately, so a later
    # slice failing never discards earlier work.
    if not allow_api:
        for candidate in missing:
            fallback = psnprofiles_search_query(candidate.game) or candidate.game
            fallback = _source_title_override(fallback)
            resolved[candidate_key(candidate)] = TitleResolution(
                fallback,
                error="沒有已快取的 Gemini 英文名稱。",
            )
        return resolved

    for start in range(0, len(missing), _TITLE_GROUNDING_BATCH_SIZE):
        batch = missing[start : start + _TITLE_GROUNDING_BATCH_SIZE]
        try:
            items = _request_resolutions(batch)
        except Exception as exc:
            logger.warning(
                "Gemini grounded title lookup failed offset=%d count=%d: %s",
                start,
                len(batch),
                exc,
            )
            for candidate in batch:
                fallback = psnprofiles_search_query(candidate.game) or candidate.game
                fallback = _source_title_override(fallback)
                resolved[candidate_key(candidate)] = TitleResolution(
                    fallback,
                    error="Gemini 暫時無法解析英文遊戲名稱。",
                )
            continue

        for index, candidate in enumerate(batch):
            item = items.get(str(index)) or {}
            fallback = psnprofiles_search_query(candidate.game) or candidate.game
            fallback = _source_title_override(fallback)
            title = psnprofiles_search_query(str(item.get("english_title") or ""))
            is_trial = bool(item.get("is_trial"))
            if title and is_english_search_title(title):
                resolution = TitleResolution(title, is_trial, "gemini")
                cache.save(
                    _cache_key(candidate),
                    {"english_title": title, "is_trial": is_trial},
                )
            else:
                resolution = TitleResolution(
                    fallback,
                    is_trial,
                    error="Gemini 沒有回傳可用的英文遊戲名稱。",
                )
            resolved[candidate_key(candidate)] = resolution

    return resolved
