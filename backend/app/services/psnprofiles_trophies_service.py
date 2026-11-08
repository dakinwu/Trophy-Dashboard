"""On-demand PSNProfiles rarity data for one trophy list."""

from __future__ import annotations

import hashlib
import logging
import re
from urllib.parse import quote_plus, urljoin, urlparse
from datetime import datetime, timezone

from bs4 import BeautifulSoup

from app.config import settings
from app.core.cache import FileCache
from app.services.http import PSNProfilesFetchError, PSNProfilesChallengeError, create_session
from app.services.psnprofiles_guide_service import (
    PSNPROFILES_BASE_URL,
    _candidate_is_safe_match,
    _candidate_score,
    _legacy_psnprofiles_search_query,
    psnprofiles_search_query,
)

logger = logging.getLogger(__name__)

PSNPROFILES_GAME_SEARCH_URL = f"{PSNPROFILES_BASE_URL}/search/games"
_TROPHY_LIST_TTL = 30 * 24 * 3600
_GAME_PATH = re.compile(r"^/trophies/\d+(?:-[^/?#]+)?/?$")
_TROPHY_PATH = re.compile(r"^/trophy/\d+(?:-[^/?#]+)?/\d+(?:-[^/?#]+)?/?$")
_PERCENT = re.compile(r"\b\d+(?:\.\d+)?%")
_RARITY_LABEL = re.compile(
    r"\b(Ultra Rare|Very Rare|Rare|Uncommon|Common)\b",
    flags=re.IGNORECASE,
)
_GAME_OWNERS = re.compile(r"\b([\d,]+)\s+Game Owners?\b", flags=re.IGNORECASE)
_AVERAGE_COMPLETION = re.compile(
    r"\b(\d+(?:\.\d+)?)%\s+Average Completion\b",
    flags=re.IGNORECASE,
)
_PLATINUM_ACHIEVERS = re.compile(
    r"\b([\d,]+)\s*\((\d+(?:\.\d+)?)%\)\s+Platinum Achievers?\b",
    flags=re.IGNORECASE,
)


class PSNProfilesTrophyReadError(PSNProfilesFetchError):
    """A matching game was found, but its trophy table was unavailable."""


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
        page_title = soup.title.get_text(" ", strip=True) if soup.title else "unknown"
        logger.warning(
            "PSNProfiles search parser found no trophy-list links query=%r page_title=%r",
            game,
            page_title,
        )
        return None

    wanted_platform = (platform or "").upper().replace(" ", "")

    def score(candidate: tuple[str, tuple[str, set[str]]]) -> float:
        _url, (title, platforms) = candidate
        value = _candidate_score(game, title)
        if wanted_platform and platforms:
            value += 0.2 if wanted_platform in platforms else -0.2
        return value

    eligible = []
    for candidate in candidates.items():
        _url, (title, platforms) = candidate
        safe_title = _candidate_is_safe_match(game, title)
        safe_platform = not wanted_platform or not platforms or wanted_platform in platforms
        if safe_title and safe_platform:
            eligible.append(candidate)
        else:
            logger.info(
                "PSNProfiles candidate rejected query=%r candidate=%r reason=%s score=%.3f platforms=%s",
                game, title, "title" if not safe_title else "platform",
                _candidate_score(game, title), ",".join(sorted(platforms)) or "UNKNOWN",
            )
    if not eligible:
        logger.warning("PSNProfiles no eligible candidates query=%r platform=%s examined=%d",
                       game, wanted_platform or "UNKNOWN", len(candidates))
        return None
    game_url, (title, platforms) = max(eligible, key=score)
    return {
        "title": title,
        "game_url": game_url,
        "platform": ",".join(sorted(platforms)),
    }


def parse_trophy_page(
    html: str,
) -> list[dict[str, str | int | list[str] | None]]:
    """Extract trophy names and tracked-player rarity from a game page."""
    soup = BeautifulSoup(html, "html.parser")
    # PSNProfiles may repeat the platinum trophy URL in a "Platinum Club"
    # sidebar before the real trophy tables. Parse every trophy table so DLC
    # groups are included, while excluding the sidebar and deduplicating URLs.
    trophy_roots = [
        table
        for table in soup.select("table.zebra")
        if table.select_one('a[href*="/trophy/"]')
    ] or [soup]
    trophies: list[dict[str, str | int | list[str] | None]] = []
    seen_urls: set[str] = set()

    for trophy_root in trophy_roots:
        for anchor in trophy_root.select("a[href]"):
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

            title_node = next(
                (
                    node
                    for node in container.select('a[href*="/trophy/"]')
                    if urljoin(PSNPROFILES_BASE_URL, node.get("href", ""))
                    == absolute_url
                    if node.get_text(" ", strip=True)
                ),
                None,
            )
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

            percentages: list[str] = []
            for node in container.select(".typo-top, .rarity, span"):
                for match in _PERCENT.finditer(node.get_text(" ", strip=True)):
                    percentage = match.group(0)
                    if percentage not in percentages:
                        percentages.append(percentage)
            if not percentages:
                percentages = list(
                    dict.fromkeys(
                        match.group(0)
                        for match in _PERCENT.finditer(
                            container.get_text(" ", strip=True)
                        )
                    )
                )

            label_match = _RARITY_LABEL.search(container.get_text(" ", strip=True))
            trophy_id_match = re.match(r"^/trophy/[^/]+/(\d+)", parsed.path)
            seen_urls.add(absolute_url)
            trophies.append(
                {
                    "trophy_id": (
                        # PSNProfiles URL positions are one-based; official PSN
                        # trophy IDs are zero-based.
                        int(trophy_id_match.group(1)) - 1
                        if trophy_id_match
                        else None
                    ),
                    "title": title,
                    # The page contains both PSNProfiles and official PSN rarity.
                    # When a site preference flips their visible order, the client
                    # uses the official value it already has to select the other
                    # candidate reliably.
                    "psnprofiles_rarity_percent": (
                        percentages[0] if percentages else None
                    ),
                    "rarity_percentages": percentages,
                    "rarity_label": (
                        label_match.group(1).title() if label_match else None
                    ),
                    "trophy_url": absolute_url,
                }
            )

    return trophies


def parse_game_stats(html: str) -> dict[str, int | float | None]:
    """Extract the game-level tracked-player signals shown by PSNProfiles."""
    text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    owners_match = _GAME_OWNERS.search(text)
    completion_match = _AVERAGE_COMPLETION.search(text)
    platinum_match = _PLATINUM_ACHIEVERS.search(text)
    return {
        "owners": (
            int(owners_match.group(1).replace(",", ""))
            if owners_match
            else None
        ),
        "average_completion": (
            float(completion_match.group(1)) if completion_match else None
        ),
        "platinum_achievers": (
            int(platinum_match.group(1).replace(",", ""))
            if platinum_match
            else None
        ),
        "platinum_rate": (
            float(platinum_match.group(2)) if platinum_match else None
        ),
    }


def get_psnprofiles_trophies(
    game: str,
    platform: str | None = None,
    *,
    search_aliases: list[str] | None = None,
    cache_only: bool = False,
    cache: FileCache | None = None,
    session=None,
) -> dict | None:
    """Resolve, fetch, and cache one PSNProfiles trophy list."""
    game = (game or "").strip()
    if not game:
        return None

    cache = cache or FileCache(settings.cache_dir)
    # Advisor/detail lookups are bounded; a single dead page must not consume
    # the full profile-scrape timeout twice before the next game is processed.
    read_timeout = min(settings.psnprofiles_browser_timeout, 45.0)
    search_titles: list[str] = []
    for title in [game, *(search_aliases or [])]:
        query = psnprofiles_search_query(title)
        if query and query.casefold() not in {
            existing.casefold() for existing in search_titles
        }:
            search_titles.append(query)
    if not search_titles:
        return None

    def cache_key(title: str) -> str:
        cache_seed = f"{title.casefold()}:{(platform or '').upper()}"
        digest = hashlib.sha256(cache_seed.encode("utf-8")).hexdigest()
        return f"psnprofiles_trophies_v7/{digest}"

    # v7 stores game-level owners / completion / platinum signals for the
    # Trophy Advisor while retaining the complete DLC-aware trophy list.
    # Failed searches are not cached, so cleaned titles and optional aliases can
    # retry them without invalidating previously successful enrichment data.
    key = cache_key(game)

    def valid_cached_result(cached: dict) -> bool:
        cached_title = str(cached.get("title") or "")
        cached_platforms = _platform_tokens(str(cached.get("platform") or ""))
        wanted_platform = (platform or "").upper().replace(" ", "")
        title_matches = any(
            _candidate_is_safe_match(search_title, cached_title)
            for search_title in search_titles
        )
        platform_matches = (
            not wanted_platform
            or not cached_platforms
            or wanted_platform in cached_platforms
        )
        return bool(cached and cached.get("trophies") and title_matches and platform_matches)

    previous: dict | None = None
    previous_key = key

    def old_result(message: str | None = None) -> dict | None:
        if previous is None:
            return None
        modified = cache.modified_at(previous_key)
        return {
            **previous,
            "cache_status": "stale",
            "fetched_at": previous.get("fetched_at") or (
                datetime.fromtimestamp(modified, timezone.utc).isoformat() if modified else None
            ),
            "refresh_error": message,
        }

    cached = cache.load(key, _TROPHY_LIST_TTL)
    if cached is not None:
        if valid_cached_result(cached):
            logger.info(
                "PSNProfiles cache hit title=%r platform=%s cached_title=%r",
                game,
                platform or "UNKNOWN",
                cached.get("title"),
            )
            return cached
        cache.delete(key)
    old = cache.load(key, float("inf"))
    if old is not None and valid_cached_result(old):
        previous = old

    # Search punctuation was tightened after Advisor analysis already existed.
    # Migrate validated legacy keys (for example ``Beyond: Two Souls``) to the
    # canonical punctuation-free key without opening Chrome again.
    legacy_titles: list[str] = []
    for title in [game, *(search_aliases or [])]:
        legacy_title = _legacy_psnprofiles_search_query(title)
        if (
            legacy_title
            and legacy_title.casefold() != game.casefold()
            and legacy_title.casefold()
            not in {existing.casefold() for existing in legacy_titles}
        ):
            legacy_titles.append(legacy_title)
    for legacy_title in legacy_titles:
        legacy_key = cache_key(legacy_title)
        legacy_cached = cache.load(legacy_key, _TROPHY_LIST_TTL)
        if legacy_cached is None:
            old = cache.load(legacy_key, float("inf"))
            if previous is None and old is not None and valid_cached_result(old):
                previous, previous_key = old, legacy_key
            continue
        if valid_cached_result(legacy_cached):
            cache.save(key, legacy_cached)
            cache.delete(legacy_key)
            logger.info(
                "PSNProfiles legacy cache migrated title=%r platform=%s cached_title=%r",
                game,
                platform or "UNKNOWN",
                legacy_cached.get("title"),
            )
            return legacy_cached
        cache.delete(legacy_key)
    if cache_only:
        if previous is not None:
            logger.info("PSNProfiles restored last success title=%r platform=%s fetched_at=%s",
                        game, platform or "UNKNOWN", old_result()["fetched_at"])
            return old_result("資料已超過更新期限，目前顯示最後一次成功的資料。")
        logger.info(
            "PSNProfiles cache miss title=%r platform=%s aliases=%r",
            game,
            platform or "UNKNOWN",
            search_titles,
        )
        return None

    owns_session = session is None
    session = session or create_session()
    try:
        match = None
        if previous is not None:
            prior_url = urlparse(str(previous.get("game_url") or ""))
            if prior_url.scheme == "https" and prior_url.netloc in {"psnprofiles.com", "www.psnprofiles.com"} and _GAME_PATH.fullmatch(prior_url.path):
                match = {"title": previous["title"], "platform": previous.get("platform", ""),
                         "game_url": str(previous["game_url"])}
                logger.info("PSNProfiles refreshing known game URL title=%r url=%s", game, match["game_url"])
        for search_title in ([] if match else search_titles):
            search_url = (
                f"{PSNPROFILES_GAME_SEARCH_URL}?q={quote_plus(search_title)}"
            )
            logger.info(
                "PSNProfiles search start title=%r platform=%s",
                search_title,
                platform or "UNKNOWN",
            )
            for attempt in range(2):
                try:
                    search_response = session.get(search_url, timeout=read_timeout)
                    search_response.raise_for_status()
                except PSNProfilesChallengeError:
                    raise
                except PSNProfilesFetchError:
                    if attempt == 1:
                        raise
                    logger.warning("PSNProfiles search read retry query=%r reason=fetch_failed", search_title)
                    continue
                match = parse_game_search(search_response.text, search_title, platform)
                if match is not None:
                    break
                logger.info("PSNProfiles search retry query=%r attempt=%d reason=no_safe_candidate",
                            search_title, attempt + 1)
            if match is not None:
                logger.info(
                    "PSNProfiles search matched title=%r platform=%s result=%r url=%s",
                    search_title,
                    platform or "UNKNOWN",
                    match["title"],
                    match["game_url"],
                )
                break
            logger.info(
                "PSNProfiles search no safe match title=%r platform=%s",
                search_title,
                platform or "UNKNOWN",
            )
        if match is None:
            logger.warning(
                "PSNProfiles lookup exhausted aliases game=%r platform=%s aliases=%r",
                game,
                platform or "UNKNOWN",
                search_titles,
            )
            return old_result("搜尋尚未找到可安全比對的遊戲，保留最後成功資料。")

        logger.info("PSNProfiles trophy page start url=%s", match["game_url"])
        trophies = []
        for attempt in range(2):
            try:
                trophy_response = session.get(
                    f"{match['game_url']}?order=rarity",
                    timeout=read_timeout,
                )
                trophy_response.raise_for_status()
            except PSNProfilesChallengeError:
                raise
            except PSNProfilesFetchError:
                if attempt == 1:
                    raise PSNProfilesTrophyReadError("已找到相符遊戲，但獎盃頁讀取失敗；請稍後重試。") from None
                logger.warning("PSNProfiles trophy read retry title=%r reason=fetch_failed", game)
                continue
            trophies = parse_trophy_page(trophy_response.text)
            if trophies:
                break
            logger.warning("PSNProfiles trophy table retry title=%r url=%s attempt=%d reason=empty_table",
                           game, match["game_url"], attempt + 1)
        if not trophies:
            logger.warning(
                "PSNProfiles trophy page contained no trophy rows url=%s",
                match["game_url"],
            )
            raise PSNProfilesTrophyReadError("已找到相符遊戲，但獎盃表格未完成載入；請重試原頁面。")

        result = {
            "title": match["title"],
            "platform": match["platform"],
            "game_url": match["game_url"],
            "trophies": trophies,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            **parse_game_stats(trophy_response.text),
        }
        cache.save(key, result)
        logger.info(
            "PSNProfiles lookup complete title=%r platform=%s trophies=%d owners=%s platinum_achievers=%s",
            result["title"],
            result["platform"] or platform or "UNKNOWN",
            len(trophies),
            result.get("owners"),
            result.get("platinum_achievers"),
        )
        return result
    except PSNProfilesFetchError as exc:
        if previous is not None:
            logger.warning("PSNProfiles refresh failed; retained last success title=%r platform=%s reason=%s",
                           game, platform or "UNKNOWN", type(exc).__name__)
            message = ("網站需要手動驗證，保留最後成功資料。" if isinstance(exc, PSNProfilesChallengeError)
                       else "更新暫時失敗，保留最後成功資料。")
            return old_result(message)
        raise
    finally:
        if owns_session:
            session.close()
