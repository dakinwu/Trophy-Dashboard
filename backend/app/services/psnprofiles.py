import logging
import math
import random
import re
import time
from typing import Callable
from urllib.parse import quote

from bs4 import BeautifulSoup

from app.config import settings
from app.models import ProfileData, ProfileSummary, TrophyCounts, Trophy

logger = logging.getLogger(__name__)


def _platforms_from_game_name(name: str) -> list[str]:
    """Best-effort fallback because PSNProfiles' trophy log omits platform data."""
    match = re.search(
        r"\((PS3|PS4|PS5|PS\s*VITA|PSVITA)\)\s*$",
        name,
        flags=re.IGNORECASE,
    )
    if not match:
        return ["UNKNOWN"]
    platform = match.group(1).upper().replace(" ", "")
    return [platform]


def _integer(text: str) -> int:
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else 0


def parse_profile_summary(html_content: str) -> ProfileSummary | None:
    soup = BeautifulSoup(html_content, "html.parser")
    try:
        user_bar = soup.select_one("#user-bar")
        if not user_bar:
            return None

        username_span = user_bar.select_one(".username")
        username = username_span.get_text(strip=True) if username_span else None
        if not username:
            return None

        avatar_url = None
        avatar_img = user_bar.select_one(".avatar img[src]")
        if avatar_img:
            avatar_url = avatar_img["src"]

        counts = TrophyCounts()
        for t_type in ["total", "platinum", "gold", "silver", "bronze"]:
            el = user_bar.select_one(f"li.{t_type}")
            if el:
                setattr(counts, t_type, _integer(el.get_text(" ", strip=True)))

        stats: dict[str, str] = {}
        stats_div = soup.select_one(".stats")
        if stats_div:
            for stat in stats_div.select("span.stat"):
                label_span = stat.find("span")
                values = list(stat.stripped_strings)
                if label_span and values:
                    stats[label_span.get_text(" ", strip=True)] = values[0].replace(",", "")

        # The current layout moved the trophy level out of `.stats` and into
        # the profile bar. Keep accepting old fixtures where Level is a stat.
        level = user_bar.select_one(".level-box .vertical > span")
        if level and "Level" not in stats:
            stats["Level"] = level.get_text(strip=True)

        return ProfileSummary(
            username=username,
            avatar_url=avatar_url,
            total_trophies=counts,
            stats=stats,
        )
    except (AttributeError, TypeError, ValueError) as e:
        logger.error("Error parsing summary: %s", e)
        return None


def parse_trophy_log_page(html_content: str) -> list[Trophy]:
    soup = BeautifulSoup(html_content, "html.parser")
    trophies: list[Trophy] = []
    trophy_table = soup.find("table", class_="zebra")
    if not trophy_table:
        return []

    for row in trophy_table.find_all("tr"):
        try:
            cells = row.find_all("td")
            if len(cells) < 10:
                continue

            game_img = cells[0].find("img")
            trophy_img = cells[1].find("img")
            title_anchor = cells[2].find("a", class_="title")
            date_span = cells[5].find("span", class_="typo-top-date")
            time_span = cells[5].find("span", class_="typo-bottom-date")
            rarity_span = cells[8].find("span", class_="typo-top")
            grade_img = cells[9].find("img")

            date_str = date_span.get_text(" ", strip=True) if date_span else ""
            date_str = re.sub(
                r"(\d+)\s+(st|nd|rd|th)\b", r"\1\2", date_str, flags=re.IGNORECASE
            )
            time_str = time_span.get_text(" ", strip=True) if time_span else ""

            trophies.append(
                Trophy(
                    game=game_img["title"] if game_img else "N/A",
                    platforms=_platforms_from_game_name(
                        game_img["title"] if game_img else ""
                    ),
                    icon_url=trophy_img["src"] if trophy_img else "N/A",
                    title=title_anchor.text.strip() if title_anchor else "N/A",
                    timestamp=f"{date_str} {time_str}".strip(),
                    rarity_percent=rarity_span.text.strip() if rarity_span else "N/A",
                    rarity_source="psnprofiles",
                    psnprofiles_rarity_percent=(
                        rarity_span.text.strip() if rarity_span else None
                    ),
                    grade=grade_img["title"] if grade_img else "N/A",
                )
            )
        except (AttributeError, TypeError, KeyError) as e:
            logger.warning("Skipping malformed row in trophy log: %s", e)
            continue

    return trophies


PSN_BASE = "https://psnprofiles.com"


def fetch_summary(session, base_url: str) -> ProfileSummary | None:
    rs = session.get(base_url, timeout=settings.psnprofiles_browser_timeout)
    rs.raise_for_status()
    return parse_profile_summary(rs.text)


def fetch_trophy_log(
    session,
    base_url: str,
    on_progress: Callable[[int], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
    total_pages: int | None = None,
) -> list[Trophy]:
    all_trophies: list[Trophy] = []
    page = 1
    session.headers.update({"Referer": base_url})

    while (total_pages is None or page <= total_pages) and (
        should_stop is None or not should_stop()
    ):
        rs = session.get(
            f"{base_url}/log?page={page}",
            timeout=settings.psnprofiles_browser_timeout,
        )
        if rs.status_code == 404:
            break
        rs.raise_for_status()

        trophies = parse_trophy_log_page(rs.text)
        if not trophies:
            break

        all_trophies.extend(trophies)
        if on_progress:
            on_progress(page)
        page += 1
        if total_pages is None or page <= total_pages:
            time.sleep(random.uniform(1.0, 2.5))

    return all_trophies


def scrape_profile(
    session,
    username: str,
    on_progress: Callable[[int, int], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> ProfileData | None:
    base_url = f"{PSN_BASE}/{quote(username, safe='')}"
    summary = fetch_summary(session, base_url)
    if summary is None or summary.total_trophies.total == 0:
        return None

    total_pages = max(1, math.ceil(summary.total_trophies.total / 50))

    def _page_progress(page: int) -> None:
        if on_progress:
            on_progress(page, total_pages)

    log = fetch_trophy_log(
        session,
        base_url,
        on_progress=_page_progress,
        should_stop=should_stop,
        total_pages=total_pages,
    )
    return ProfileData(profile_summary=summary, trophy_log=log)
