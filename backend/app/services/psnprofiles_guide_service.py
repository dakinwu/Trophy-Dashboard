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
_SEARCH_DECORATION = re.compile(r"[™®©℠]")
_SEARCH_PUNCTUATION = re.compile(r"[:：|/\\]+")
_PLATFORM_SUFFIX = re.compile(
    r"(?:\s*[-–—:|]?\s*[\[(]?\s*(?:PS[345]|PlayStation\s*[345])\s*[\])]?)$",
    flags=re.IGNORECASE,
)
_GENERIC_TITLE_TOKENS = {
    "a",
    "an",
    "and",
    "collection",
    "complete",
    "deathinitive",
    "definitive",
    "deluxe",
    "edition",
    "game",
    "of",
    "remake",
    "remastered",
    "the",
    "trophies",
    "trophy",
    "ultimate",
}
# Roman numerals I-XXXIX, as used in sequel titles (Final Fantasy XVI).
_ROMAN_TOKEN = re.compile(r"^x{0,3}(?:ix|iv|v?i{0,3})$")
_ROMAN_DIGITS = {"i": 1, "v": 5, "x": 10}
_ROMAN_PARTS = ((10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"))
# A standalone number or Roman-numeral word inside a search title.
_NUMERAL_WORD = re.compile(r"(?<![\w'])(?:\d{1,2}|[IVXivx]{1,6})(?![\w'])")
# Sequel numbers worth retrying as Roman numerals; larger ones are usually
# years or sports editions (F1 25), which PSNProfiles never writes as Roman.
_MAX_ROMAN_SEQUEL = 20


def roman_numeral_value(token: str) -> int | None:
    """Value of a Roman-numeral word (``xvi`` -> 16), else None."""
    token = token.casefold()
    if not token or not _ROMAN_TOKEN.fullmatch(token):
        return None
    total = previous = 0
    for char in reversed(token):
        value = _ROMAN_DIGITS[char]
        if value < previous:
            total -= value
        else:
            total += value
            previous = value
    return total


def _to_roman(number: int) -> str:
    parts = []
    for value, numeral in _ROMAN_PARTS:
        count, number = divmod(number, value)
        parts.append(numeral * count)
    return "".join(parts)


def numeral_search_variants(title: str) -> list[str]:
    """Alternative search titles with sequel numbers in the other notation.

    PSNProfiles search does not equate "Final Fantasy 16" with "Final Fantasy
    XVI", so a failed search is retried with Arabic numbers written as Roman
    numerals and vice versa. A lone "I" is left alone (usually the pronoun).
    """

    def arabic_to_roman(match: re.Match) -> str:
        token = match.group(0)
        if token.isdigit() and 2 <= int(token) <= _MAX_ROMAN_SEQUEL:
            return _to_roman(int(token))
        return token

    def roman_to_arabic(match: re.Match) -> str:
        token = match.group(0)
        value = None if token.casefold() == "i" else roman_numeral_value(token)
        return str(value) if value else token

    variants: list[str] = []
    for convert in (arabic_to_roman, roman_to_arabic):
        variant = _NUMERAL_WORD.sub(convert, title)
        if variant != title and variant not in variants:
            variants.append(variant)
    return variants


# Store/marketing edition suffixes PSNProfiles often omits from list names
# (the PS4 "Mafia II: Definitive Edition" list is just "Mafia II"). A bare
# "Enhanced" covers store translations such as 赤血沙漠：強化版.
_EDITION_SUFFIX = re.compile(
    r"\s+(?:(?:definitive|complete|deluxe|digital\s+deluxe|ultimate|special|"
    r"enhanced|anniversary|legendary|gold|standard|game\s+of\s+the\s+year|goty)"
    r"\s+edition|enhanced|remastered|remaster|director'?s\s+cut|goty)$",
    flags=re.IGNORECASE,
)


def _strip_edition_suffix(title: str) -> str:
    stripped = title.strip()
    while (shorter := _EDITION_SUFFIX.sub("", stripped).strip()) != stripped:
        stripped = shorter
    has_name = any(
        token not in _GENERIC_TITLE_TOKENS for token in _normalise_title(stripped).split()
    )
    return stripped if has_name else title


def fallback_search_titles(titles: list[str]) -> list[str]:
    """Search titles in the order to try them, stopping at the first match.

    The given titles come first, then the same titles with sequel numbers in
    the other notation (16 <-> XVI), then without edition suffixes such as
    "Definitive Edition" or "Remastered" (and their numeral variants).
    """
    ordered: list[str] = []
    seen: set[str] = set()
    shortened = [
        short for title in titles if (short := _strip_edition_suffix(title)) != title
    ]
    for group in (titles, shortened):
        candidates = [*group, *(v for t in group for v in numeral_search_variants(t))]
        for title in (candidate.strip() for candidate in candidates):
            if title and title.casefold() not in seen:
                seen.add(title.casefold())
                ordered.append(title)
    return ordered


def _legacy_psnprofiles_search_query(title: str) -> str:
    """Reproduce the pre-punctuation-cleanup title for cache migration."""
    # Remove trademark glyphs before NFKC; otherwise ``™`` becomes the letters
    # ``TM`` and PSNProfiles treats it as part of the title search.
    cleaned = _SEARCH_DECORATION.sub("", title or "")
    cleaned = unicodedata.normalize("NFKC", cleaned)
    cleaned = _PLATFORM_SUFFIX.sub("", cleaned)
    return _SPACE.sub(" ", cleaned).strip(" \t\r\n-–—:|")


def psnprofiles_search_query(title: str) -> str:
    """Return a PSNProfiles-friendly title without store decorations."""
    cleaned = _legacy_psnprofiles_search_query(title)
    cleaned = _SEARCH_PUNCTUATION.sub(" ", cleaned)
    return _SPACE.sub(" ", cleaned).strip()


def _normalise_title(title: str) -> str:
    title = unicodedata.normalize("NFKC", title).casefold()
    title = title.replace("&", " and ")
    title = re.sub(r"\btrophy\s+guide\b", " ", title)
    title = re.sub(r"\b(ps[345]|playstation\s*[345])\b", " ", title)
    tokens = _SPACE.sub(" ", _NON_WORD.sub(" ", title)).strip().split()
    # Compare sequel numbers by value: "xvi" and "16" are the same token. A lone
    # "i" stays a word (usually the pronoun, as in "I Am Setsuna").
    return " ".join(
        str(value) if token != "i" and (value := roman_numeral_value(token)) else token
        for token in tokens
    )


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


def _candidate_is_safe_match(game: str, candidate: str) -> bool:
    """Reject PSNProfiles' loose search results that only share one word."""
    wanted = _normalise_title(game)
    actual = _normalise_title(candidate)
    if not wanted or not actual:
        return False
    if wanted == actual:
        return True
    wanted_all = wanted.split()
    actual_all = actual.split()
    def sequel_markers(tokens: list[str]) -> set[int]:
        # Roman numerals were already normalised to digits, except a lone "i".
        return {
            int(token) if token.isdigit() else 1
            for token in tokens
            if token.isdigit() or token == "i"
        }

    wanted_sequels = sequel_markers(wanted_all)
    actual_sequels = sequel_markers(actual_all)
    if wanted_sequels != actual_sequels and (wanted_sequels or actual_sequels):
        return False
    wanted_tokens = {
        token for token in wanted_all if token not in _GENERIC_TITLE_TOKENS
    }
    actual_tokens = {
        token for token in actual_all if token not in _GENERIC_TITLE_TOKENS
    }
    if not wanted_tokens or not actual_tokens:
        return False
    if wanted_tokens == actual_tokens:
        return True
    common = wanted_tokens & actual_tokens
    # A one-word title occurring inside another title (Journey / Blue's Journey,
    # Evolve / Revolved) is not enough evidence for a safe cache or search match.
    if len(wanted_tokens) == 1 or len(actual_tokens) == 1:
        return False
    wanted_coverage = len(common) / len(wanted_tokens)
    actual_coverage = len(common) / len(actual_tokens)
    return (
        _candidate_score(game, candidate) >= 0.72
        and wanted_coverage >= 0.75
        and actual_coverage >= 0.6
    )


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
    if not _candidate_is_safe_match(game, title):
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
    search_query = psnprofiles_search_query(game)
    if not search_query:
        return None

    cache = cache or FileCache(settings.cache_dir)
    digest = hashlib.sha256(search_query.casefold().encode("utf-8")).hexdigest()
    key = f"psnprofiles_guide/{digest}"
    cached = cache.load(key, _GUIDE_TTL)
    if cached is not None:
        return cached or None

    owns_session = session is None
    session = session or create_session()
    try:
        search_url = (
            f"{PSNPROFILES_GUIDE_SEARCH_URL}?q={quote_plus(search_query)}"
        )
        search_response = session.get(
            search_url,
            timeout=settings.psnprofiles_browser_timeout,
        )
        search_response.raise_for_status()
        match = parse_guide_search(search_response.text, search_query)
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
