import logging
import math
import random
import time
from typing import Callable

from bs4 import BeautifulSoup

from app.models import ProfileData, ProfileSummary, TrophyCounts, Trophy

logger = logging.getLogger(__name__)


def parse_profile_summary(html_content: str) -> ProfileSummary | None:
    soup = BeautifulSoup(html_content, "html.parser")
    try:
        user_bar = soup.find("div", id="user-bar")
        if not user_bar:
            return None

        username_span = user_bar.find("span", class_="username")
        username = username_span.text.strip() if username_span else None
        if not username:
            return None

        avatar_url = None
        avatar_div = user_bar.find("div", class_="avatar")
        if avatar_div:
            avatar_img = avatar_div.find("img")
            if avatar_img and avatar_img.has_attr("src"):
                avatar_url = avatar_img["src"]

        counts = TrophyCounts()
        for t_type in ["total", "platinum", "gold", "silver", "bronze"]:
            el = user_bar.find("li", class_=t_type)
            if el:
                setattr(counts, t_type, int(el.text.strip().replace(",", "")))

        stats: dict[str, str] = {}
        stats_div = soup.find("div", class_="stats")
        if stats_div:
            for stat in stats_div.find_all("span", class_="stat"):
                value = stat.contents[0].strip().replace(",", "")
                label_span = stat.find("span")
                if label_span:
                    stats[label_span.text.strip()] = value

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

            date_str = date_span.text.strip() if date_span else ""
            time_str = time_span.text.strip() if time_span else ""

            trophies.append(
                Trophy(
                    game=game_img["title"] if game_img else "N/A",
                    icon_url=trophy_img["src"] if trophy_img else "N/A",
                    title=title_anchor.text.strip() if title_anchor else "N/A",
                    timestamp=f"{date_str} {time_str}".strip(),
                    rarity_percent=rarity_span.text.strip() if rarity_span else "N/A",
                    grade=grade_img["title"] if grade_img else "N/A",
                )
            )
        except (AttributeError, TypeError, KeyError) as e:
            logger.warning("Skipping malformed row in trophy log: %s", e)
            continue

    return trophies


PSN_BASE = "https://psnprofiles.com"


def fetch_summary(session, base_url: str) -> ProfileSummary | None:
    rs = session.get(base_url, timeout=15)
    rs.raise_for_status()
    return parse_profile_summary(rs.text)


def fetch_trophy_log(
    session,
    base_url: str,
    on_progress: Callable[[int], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> list[Trophy]:
    all_trophies: list[Trophy] = []
    page = 1
    session.headers.update({"Referer": base_url})

    while should_stop is None or not should_stop():
        rs = session.get(f"{base_url}/log?page={page}", timeout=15)
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
        time.sleep(random.uniform(1.0, 2.5))

    return all_trophies


def scrape_profile(
    session,
    username: str,
    on_progress: Callable[[int, int], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> ProfileData | None:
    base_url = f"{PSN_BASE}/{username}"
    summary = fetch_summary(session, base_url)
    if summary is None or summary.total_trophies.total == 0:
        return None

    total_pages = max(1, math.ceil(summary.total_trophies.total / 50))

    def _page_progress(page: int) -> None:
        if on_progress:
            on_progress(page, total_pages)

    log = fetch_trophy_log(
        session, base_url, on_progress=_page_progress, should_stop=should_stop
    )
    return ProfileData(profile_summary=summary, trophy_log=log)
