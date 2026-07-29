"""On-demand PSNProfiles rarity data for one trophy list."""

from __future__ import annotations

import hashlib
import re
from urllib.parse import quote_plus, urljoin, urlparse

from bs4 import BeautifulSoup

from app.config import settings
from app.core.cache import FileCache
from app.services.http import create_session
from app.services.psnprofiles_guide_service import (
    PSNPROFILES_BASE_URL,
    _candidate_score,
)

PSNPROFILES_GAME_SEARCH_URL = f"{PSNPROFILES_BASE_URL}/search/games"
_TROPHY_LIST_TTL = 30 * 24 * 3600
_GAME_PATH = re.compile(r"^/trophies/\d+(?:-[^/?#]+)?/?$")
_TROPHY_PATH = re.compile(r"^/trophy/\d+(?:-[^/?#]+)?/\d+(?:-[^/?#]+)?/?$")
_PERCENT = re.compile(r"\b\d+(?:\.\d+)?%")
_RARITY_LABEL = re.compile(
    r"\b(Ultra Rare|Very Rare|Rare|Uncommon|Common)\b",
    flags=re.IGNORECASE,
)


def _platform_tokens(text: str) -> set[str]:
    tokens = {
        match.upper().replace(" ", "")
        for match in re.findall(
            r"\b(PS3|PS4|PS5|PS\s*VITA|PSVITA)\b",
            text,
            flags=re.IGNORECASE,
        )
    }
    return {"PSVITA" if token == "PSVITA" else token for token in tokens}


def parse_game_search(
    html: str,
    game: str,
    platform: str | None = None,
) -> dict[str, str] | None:
    """Select the best title/platform match from PSNProfiles game search."""
    soup = BeautifulSoup(html, "html.parser")
    candidates: dict[str, tuple[str, set[str]]] = {}

    for anchor in soup.select("a[href]"):
        absolute_url = urljoin(PSNPROFILES_BASE_URL, anchor.get("href", ""))
        parsed = urlparse(absolute_url)
        if parsed.netloc not in {"psnprofiles.com", "www.psnprofiles.com"}:
            continue
        if not _GAME_PATH.match(parsed.path):
            continue

        container = anchor.find_parent(["tr", "article", "li", "div"])
        image = anchor.find("img")
        title_node = container.select_one(".title") if container else None
        title_options = [
            anchor.get_text(" ", strip=True),
            anchor.get("title", "").strip(),
            image.get("alt", "").strip() if image else "",
            image.get("title", "").strip() if image else "",
            title_node.get_text(" ", strip=True) if title_node else "",
        ]
        title = max(title_options, key=lambda value: _candidate_score(game, value))
        if not title:
            continue
        container_text = container.get_text(" ", strip=True) if container else title
        candidates.setdefault(
            absolute_url.rstrip("/"),
            (title, _platform_tokens(container_text)),
        )

    if not candidates:
        return None

    wanted_platform = (platform or "").upper().replace(" ", "")

    def score(candidate: tuple[str, tuple[str, set[str]]]) -> float:
        _url, (title, platforms) = candidate
        value = _candidate_score(game, title)
        if wanted_platform and platforms:
            value += 0.2 if wanted_platform in platforms else -0.2
        return value

    game_url, (title, platforms) = max(candidates.items(), key=score)
    if _candidate_score(game, title) < 0.45:
        return None
    return {
        "title": title,
        "game_url": game_url,
        "platform": ",".join(sorted(platforms)),
    }


def parse_trophy_page(html: str) -> list[dict[str, str | int | None]]:
    """Extract trophy names and tracked-player rarity from a game page."""
    soup = BeautifulSoup(html, "html.parser")
    trophies: list[dict[str, str | int | None]] = []
    seen_urls: set[str] = set()

    for anchor in soup.select("a[href]"):
        absolute_url = urljoin(PSNPROFILES_BASE_URL, anchor.get("href", ""))
        if absolute_url in seen_urls:
            continue
        parsed = urlparse(absolute_url)
        if not _TROPHY_PATH.match(parsed.path):
            continue

        container = anchor.find_parent(["tr", "li", "article"])
        if container is None:
            container = anchor.find_parent("div")
        if container is None:
            continue

        title_node = container.select_one("a.title")
        if title_node is None:
            title_node = next(
                (
                    node
                    for node in container.select('a[href*="/trophy/"]')
                    if node.get_text(" ", strip=True)
                ),
                None,
            )
        title = title_node.get_text(" ", strip=True) if title_node else ""
        if not title:
            continue

        percentage: str | None = None
        for node in container.select(".typo-top, .rarity, span"):
            match = _PERCENT.search(node.get_text(" ", strip=True))
            if match:
                percentage = match.group(0)
                break
        if percentage is None:
            match = _PERCENT.search(container.get_text(" ", strip=True))
            percentage = match.group(0) if match else None

        label_match = _RARITY_LABEL.search(container.get_text(" ", strip=True))
        trophy_id_match = re.match(r"^/trophy/[^/]+/(\d+)", parsed.path)
        seen_urls.add(absolute_url)
        trophies.append(
            {
                "trophy_id": (
                    int(trophy_id_match.group(1)) if trophy_id_match else None
                ),
                "title": title,
                "psnprofiles_rarity_percent": percentage,
                "rarity_label": (
                    label_match.group(1).title() if label_match else None
                ),
                "trophy_url": absolute_url,
            }
        )

    return trophies


def get_psnprofiles_trophies(
    game: str,
    platform: str | None = None,
    *,
    cache: FileCache | None = None,
    session=None,
) -> dict | None:
    """Resolve, fetch, and cache one PSNProfiles trophy list."""
    game = (game or "").strip()
    if not game:
        return None

    cache = cache or FileCache(settings.cache_dir)
    cache_seed = f"{game.casefold()}:{(platform or '').upper()}"
    digest = hashlib.sha256(cache_seed.encode("utf-8")).hexdigest()
    key = f"psnprofiles_trophies_v1/{digest}"
    cached = cache.load(key, _TROPHY_LIST_TTL)
    if cached is not None:
        return cached or None

    owns_session = session is None
    session = session or create_session()
    try:
        search_url = f"{PSNPROFILES_GAME_SEARCH_URL}?q={quote_plus(game)}"
        search_response = session.get(
            search_url,
            timeout=settings.psnprofiles_browser_timeout,
        )
        search_response.raise_for_status()
        match = parse_game_search(search_response.text, game, platform)
        if match is None:
            return None

        trophy_response = session.get(
            match["game_url"],
            timeout=settings.psnprofiles_browser_timeout,
        )
        trophy_response.raise_for_status()
        trophies = parse_trophy_page(trophy_response.text)
        if not trophies:
            return None

        result = {
            "title": match["title"],
            "platform": match["platform"],
            "game_url": match["game_url"],
            "trophies": trophies,
        }
        cache.save(key, result)
        return result
    finally:
        if owns_session:
            session.close()
