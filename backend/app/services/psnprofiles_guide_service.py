"""On-demand PSNProfiles trophy-guide enrichment.

Guide pages are game-level data, so successful lookups are cached for a long
time. A lookup deliberately happens only when the frontend asks for one: each
cache miss may need a visible Chrome window to pass Cloudflare.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from difflib import SequenceMatcher
from urllib.parse import quote_plus, urljoin, urlparse

from bs4 import BeautifulSoup

from app.config import settings
from app.core.cache import FileCache
from app.services.http import create_session

PSNPROFILES_BASE_URL = "https://psnprofiles.com"
PSNPROFILES_GUIDE_SEARCH_URL = f"{PSNPROFILES_BASE_URL}/search/guides"
_GUIDE_TTL = 90 * 24 * 3600
_GUIDE_PATH = re.compile(r"^/guide/\d+(?:-[^/?#]+)?/?$")
_SPACE = re.compile(r"\s+")
_NON_WORD = re.compile(r"[^\w]+", re.UNICODE)


def _normalise_title(title: str) -> str:
    title = unicodedata.normalize("NFKC", title).casefold()
    title = title.replace("&", " and ")
    title = re.sub(r"\btrophy\s+guide\b", " ", title)
    title = re.sub(r"\b(ps[345]|playstation\s*[345])\b", " ", title)
    return _SPACE.sub(" ", _NON_WORD.sub(" ", title)).strip()


def _candidate_score(game: str, candidate: str) -> float:
    wanted = _normalise_title(game)
    actual = _normalise_title(candidate)
    if not wanted or not actual:
        return 0.0
    if wanted == actual:
        return 1.0
    if min(len(wanted), len(actual)) >= 5 and (
        wanted in actual or actual in wanted
    ):
        return 0.92
    return SequenceMatcher(None, wanted, actual).ratio()


def parse_guide_search(html: str, game: str) -> dict[str, str] | None:
    """Return the best matching ``{title, guide_url}`` from guide search HTML."""
    soup = BeautifulSoup(html, "html.parser")
    candidates: dict[str, str] = {}

    for anchor in soup.select("a[href]"):
        href = anchor.get("href", "")
        absolute_url = urljoin(PSNPROFILES_BASE_URL, href)
        if urlparse(absolute_url).netloc not in {
            "psnprofiles.com",
            "www.psnprofiles.com",
        }:
            continue
        if not _GUIDE_PATH.match(urlparse(absolute_url).path):
            continue

        container = anchor.find_parent(["article", "li", "tr", "div"])
        heading = container.find(["h1", "h2", "h3", "h4"]) if container else None
        image = anchor.find("img")
        possible_titles = [
            anchor.get_text(" ", strip=True),
            anchor.get("title", "").strip(),
            heading.get_text(" ", strip=True) if heading else "",
            image.get("alt", "").strip() if image else "",
        ]
        title = max(possible_titles, key=lambda value: _candidate_score(game, value))
        if title:
            candidates.setdefault(absolute_url.rstrip("/"), title)

    if not candidates:
        return None

    guide_url, title = max(
        candidates.items(),
        key=lambda item: _candidate_score(game, item[1]),
    )
    if _candidate_score(game, title) < 0.45:
        return None
    return {"title": title, "guide_url": guide_url}


def _overview_pairs(soup: BeautifulSoup) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []

    for row in soup.select("tr"):
        cells = row.find_all(["th", "td"], recursive=False)
        if len(cells) >= 2:
            label = cells[0].get_text(" ", strip=True)
            value = " ".join(cell.get_text(" ", strip=True) for cell in cells[1:])
            if label and value:
                pairs.append((label, value))

    for term in soup.select("dt"):
        value_node = term.find_next_sibling("dd")
        if value_node:
            pairs.append(
                (
                    term.get_text(" ", strip=True),
                    value_node.get_text(" ", strip=True),
                )
            )

    for node in soup.select("li, p"):
        text = node.get_text(" ", strip=True)
        if ":" in text:
            label, value = text.split(":", 1)
            if label.strip() and value.strip():
                pairs.append((label, value))

    return pairs


def parse_guide_page(html: str, guide_url: str) -> dict[str, str | None]:
    """Parse the guide overview fields used by the dashboard."""
    soup = BeautifulSoup(html, "html.parser")
    heading = soup.select_one("h1")
    title = heading.get_text(" ", strip=True) if heading else None
    difficulty: str | None = None
    platinum_time: str | None = None

    for raw_label, raw_value in _overview_pairs(soup):
        label = _SPACE.sub(" ", raw_label).strip(" :*").casefold()
        value = _SPACE.sub(" ", raw_value).strip()
        if difficulty is None and "trophy difficulty" in label:
            difficulty = value
        if (
            platinum_time is None
            and "time" in label
            and ("platinum" in label or "completion" in label)
        ):
            platinum_time = value

    return {
        "title": title,
        "guide_url": guide_url,
        "difficulty": difficulty,
        "platinum_time": platinum_time,
    }


def get_psnprofiles_guide(
    game: str,
    *,
    cache: FileCache | None = None,
    session=None,
) -> dict[str, str | None] | None:
    """Resolve and cache one game's PSNProfiles trophy-guide metadata."""
    game = (game or "").strip()
    if not game:
        return None

    cache = cache or FileCache(settings.cache_dir)
    digest = hashlib.sha256(game.casefold().encode("utf-8")).hexdigest()
    key = f"psnprofiles_guide/{digest}"
    cached = cache.load(key, _GUIDE_TTL)
    if cached is not None:
        return cached or None

    owns_session = session is None
    session = session or create_session()
    try:
        search_url = f"{PSNPROFILES_GUIDE_SEARCH_URL}?q={quote_plus(game)}"
        search_response = session.get(
            search_url,
            timeout=settings.psnprofiles_browser_timeout,
        )
        search_response.raise_for_status()
        match = parse_guide_search(search_response.text, game)
        if match is None:
            return None

        guide_response = session.get(
            match["guide_url"],
            timeout=settings.psnprofiles_browser_timeout,
        )
        guide_response.raise_for_status()
        result = parse_guide_page(guide_response.text, match["guide_url"])
        result["title"] = result["title"] or match["title"]
        cache.save(key, result)
        return result
    finally:
        if owns_session:
            session.close()
