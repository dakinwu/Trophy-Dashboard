"""Resolve multi-game PlayStation packages with optional Search grounding."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import requests

from app.config import settings
from app.core.cache import FileCache
from app.models import AdvisorCandidate, Platform
from app.services.gemini_title_service import (
    candidate_key,
    is_english_search_title,
)
from app.services.psnprofiles_guide_service import psnprofiles_search_query

logger = logging.getLogger(__name__)

_BUNDLE_TTL = 180 * 24 * 3600
_BUNDLE_MARKER = re.compile(
    r"\b(collection|bundle|anthology|trilogy|compilation)\b|"
    r"合集|合輯|套裝|合輯版|コレクション|トリロジー",
    flags=re.IGNORECASE,
)
_KNOWN_BUNDLES: dict[str, tuple[str, ...]] = {
    "bioshock the collection": (
        "BioShock Remastered",
        "BioShock 2 Remastered",
        "BioShock Infinite",
    ),
    "borderlands the handsome collection": (
        "Borderlands 2",
        "Borderlands: The Pre-Sequel",
    ),
    "lego harry potter collection": (
        "LEGO Harry Potter: Years 1-4",
        "LEGO Harry Potter: Years 5-7",
    ),
    "uncharted the nathan drake collection": (
        "Uncharted: Drake's Fortune Remastered",
        "Uncharted 2: Among Thieves Remastered",
        "Uncharted 3: Drake's Deception Remastered",
    ),
}
_SINGLE_LIST_ANTHOLOGY_PREFIXES = ("the dark pictures anthology",)
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


@dataclass(frozen=True)
class BundleChild:
    game: str
    platform: Platform | None


@dataclass(frozen=True)
class BundleResolution:
    children: tuple[BundleChild, ...]
    source: str
    source_urls: tuple[str, ...]
    verified_at: str
    error: str | None = None


def _normalized_title(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _known_resolution(
    candidate: AdvisorCandidate,
    resolved_title: str,
) -> BundleResolution | None:
    names = [candidate.game, *candidate.aliases, resolved_title]
    for name in names:
        children = _KNOWN_BUNDLES.get(_normalized_title(name))
        if children is None:
            continue
        return BundleResolution(
            children=tuple(
                BundleChild(game=child, platform=candidate.platform)
                for child in children
            ),
            source="curated",
            source_urls=(),
            verified_at=datetime.now(timezone.utc).date().isoformat(),
        )
    return None


def _looks_like_bundle(candidate: AdvisorCandidate, resolved_title: str) -> bool:
    normalized_names = [
        _normalized_title(name)
        for name in [candidate.game, *candidate.aliases, resolved_title]
    ]
    if any(
        name.startswith(prefix)
        for name in normalized_names
        for prefix in _SINGLE_LIST_ANTHOLOGY_PREFIXES
    ):
        return False
    return any(
        _BUNDLE_MARKER.search(name or "") is not None
        for name in [candidate.game, *candidate.aliases, resolved_title]
    )


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
    return f"gemini_grounded_bundle_v1/{digest}"


def _response_text(payload: dict) -> str:
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("Gemini did not return a candidate")
    parts = (candidates[0].get("content") or {}).get("parts") or []
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
        raise ValueError("Gemini returned an empty response")
    return text


def _grounding_urls(payload: dict) -> tuple[str, ...]:
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return ()
    metadata = candidates[0].get("groundingMetadata") or {}
    urls: list[str] = []
    for chunk in metadata.get("groundingChunks") or []:
        web = chunk.get("web") if isinstance(chunk, dict) else None
        uri = str((web or {}).get("uri") or "").strip()
        if uri.startswith("https://") and uri not in urls:
            urls.append(uri)
    return tuple(urls[:12])


def _request_grounded_bundles(
    records: list[tuple[AdvisorCandidate, str]],
) -> tuple[dict[str, dict], tuple[str, ...]]:
    inputs = [
        {
            "id": str(index),
            "names": [candidate.game, *candidate.aliases, resolved_title],
            "platform": candidate.platform,
            "title_id": candidate.title_id,
            "product_id": candidate.product_id,
        }
        for index, (candidate, resolved_title) in enumerate(records)
    ]
    prompt = (
        "Use Google Search to research these PlayStation Store packages. For each "
        "input, determine whether it contains multiple games with separate trophy "
        "lists on PSNProfiles. Return only real playable games with their canonical "
        "English PSNProfiles search titles; exclude DLC, bonus content, artbooks, "
        "soundtracks, demos, trials, and duplicate regional editions. If the package "
        "has only one trophy list, set separate_trophy_lists=false and return no "
        "children. Preserve every id. Reply with JSON only in this exact shape: "
        '{"collections":[{"id":"0","separate_trophy_lists":true,'
        '"children":[{"english_title":"Game","platform":"PS4"}]}]}. '
        "Allowed platform values are PS3, PS4, PS5, PSVITA, or UNKNOWN.\n\n"
        f"Packages:\n{json.dumps(inputs, ensure_ascii=False)}"
    )
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_grounding_model}:generateContent"
    )
    logger.info(
        "Gemini grounded bundle lookup start model=%s count=%d",
        settings.gemini_grounding_model,
        len(records),
    )
    request_kwargs = {
        "headers": {
            "Content-Type": "application/json",
            "x-goog-api-key": settings.gemini_api_key or "",
        },
        "json": {
            "contents": [{"parts": [{"text": prompt}]}],
            "tools": [{"google_search": {}}],
            "generationConfig": {"temperature": 0},
        },
        "timeout": settings.gemini_timeout,
    }
    payload = None
    last_error: Exception | None = None
    for attempt in range(2):
        response = requests.post(url, **request_kwargs)
        status_code = int(getattr(response, "status_code", 200))
        if status_code in _RETRYABLE_STATUS_CODES and attempt == 0:
            logger.warning(
                "Gemini grounded bundle lookup transient HTTP %d; retrying once model=%s count=%d",
                status_code,
                settings.gemini_grounding_model,
                len(records),
            )
            time.sleep(1)
            continue
        response.raise_for_status()
        payload = response.json()
        try:
            parsed = json.loads(_response_text(payload))
            break
        except (ValueError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt == 0:
                finish_reason = (
                    ((payload.get("candidates") or [{}])[0]).get("finishReason")
                    if isinstance(payload, dict)
                    else None
                )
                logger.warning(
                    "Gemini grounded bundle lookup returned unusable content finish_reason=%s; retrying once",
                    finish_reason or "UNKNOWN",
                )
                time.sleep(1)
                continue
            raise
    else:
        raise last_error or RuntimeError("Gemini grounded lookup failed")
    if payload is None:
        raise last_error or RuntimeError("Gemini grounded lookup returned no payload")
    collections = parsed.get("collections")
    if not isinstance(collections, list):
        raise ValueError("Gemini response did not contain collections")
    logger.info(
        "Gemini grounded bundle lookup complete model=%s count=%d",
        settings.gemini_grounding_model,
        len(records),
    )
    return (
        {
            str(item.get("id")): item
            for item in collections
            if isinstance(item, dict) and item.get("id") is not None
        },
        _grounding_urls(payload),
    )


def _deserialize(cached: dict) -> BundleResolution | None:
    if not cached.get("separate_trophy_lists"):
        return None
    children: list[BundleChild] = []
    for item in cached.get("children") or []:
        if not isinstance(item, dict):
            continue
        title = str(item.get("game") or "").strip()
        platform = str(item.get("platform") or "UNKNOWN").upper()
        if title and is_english_search_title(title):
            children.append(
                BundleChild(
                    game=title,
                    platform=platform if platform in {"PS3", "PS4", "PS5", "PSVITA", "UNKNOWN"} else "UNKNOWN",  # type: ignore[arg-type]
                )
            )
    if not children:
        return None
    return BundleResolution(
        children=tuple(children),
        source="gemini_grounding",
        source_urls=tuple(str(url) for url in cached.get("source_urls") or []),
        verified_at=str(cached.get("verified_at") or ""),
    )


def resolve_advisor_bundles(
    candidates: list[AdvisorCandidate],
    resolved_titles: dict[str, str],
    *,
    cache: FileCache,
    allow_api: bool,
) -> dict[str, BundleResolution]:
    """Resolve known/cached bundles and ground all unknown bundles in one call."""
    results: dict[str, BundleResolution] = {}
    missing: list[tuple[AdvisorCandidate, str]] = []

    for candidate in candidates:
        key = candidate_key(candidate)
        resolved_title = resolved_titles[key]
        known = _known_resolution(candidate, resolved_title)
        if known is not None:
            results[key] = known
            continue
        if not _looks_like_bundle(candidate, resolved_title):
            continue
        cached = cache.load(_cache_key(candidate), _BUNDLE_TTL)
        if cached is not None:
            cached_resolution = _deserialize(cached)
            if cached_resolution is not None:
                results[key] = cached_resolution
            continue
        if not allow_api:
            results[key] = BundleResolution(
                children=(),
                source="gemini_grounding",
                source_urls=(),
                verified_at=datetime.now(timezone.utc).date().isoformat(),
                error="尚未快取這個合集的內容；按下分析後才會使用 Search grounding。",
            )
            continue
        if settings.gemini_api_key:
            missing.append((candidate, resolved_title))
        else:
            results[key] = BundleResolution(
                children=(),
                source="gemini_grounding",
                source_urls=(),
                verified_at=datetime.now(timezone.utc).date().isoformat(),
                error="請先在 .env 設定 GEMINI_API_KEY，才能查找未知合集內容。",
            )

    if not missing:
        return results

    try:
        items, source_urls = _request_grounded_bundles(missing)
    except Exception as exc:
        logger.warning("Gemini grounded bundle lookup failed: %s", exc)
        for candidate, _resolved_title in missing:
            results[candidate_key(candidate)] = BundleResolution(
                children=(),
                source="gemini_grounding",
                source_urls=(),
                verified_at=datetime.now(timezone.utc).date().isoformat(),
                error="Gemini Search grounding 暫時無法查出這個合集的內容。",
            )
        return results

    verified_at = datetime.now(timezone.utc).date().isoformat()
    for index, (candidate, _resolved_title) in enumerate(missing):
        item = items.get(str(index)) or {}
        children: list[dict[str, str]] = []
        if item.get("separate_trophy_lists") is True:
            seen: set[str] = set()
            for child in item.get("children") or []:
                if not isinstance(child, dict):
                    continue
                title = psnprofiles_search_query(
                    str(child.get("english_title") or "")
                )
                if not title or not is_english_search_title(title):
                    continue
                normalized = title.casefold()
                if normalized in seen:
                    continue
                seen.add(normalized)
                platform = str(child.get("platform") or candidate.platform or "UNKNOWN").upper()
                if platform not in {"PS3", "PS4", "PS5", "PSVITA", "UNKNOWN"}:
                    platform = candidate.platform or "UNKNOWN"
                children.append({"game": title, "platform": platform})

        cached = {
            "separate_trophy_lists": bool(children),
            "children": children,
            "source_urls": list(source_urls),
            "verified_at": verified_at,
        }
        cache.save(_cache_key(candidate), cached)
        resolution = _deserialize(cached)
        if resolution is not None:
            results[candidate_key(candidate)] = resolution

    return results
