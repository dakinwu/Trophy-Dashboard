from __future__ import annotations

import asyncio
import logging
import re
import threading
import time
from contextlib import suppress
from dataclasses import dataclass
from urllib.parse import parse_qs, urlsplit

from bs4 import BeautifulSoup

from app.config import settings

logger = logging.getLogger(__name__)

_browser_profile_lock = threading.Lock()
_TROPHY_TOTAL = re.compile(
    r"\b([\d,]+)\s+trophies\s*[•·]\s*[\d,]+\s+points\b",
    flags=re.IGNORECASE,
)
_TROPHY_LINK = re.compile(
    r"/trophy/\d+(?:-[^/?#]+)?/(\d+)(?:-[^/?#]+)?/?$",
)
_ERROR_MARKERS = (
    "profile is private",
    "profile not found",
    "user not found",
    "no user found",
    "no guides found",
    "no guide found",
    "no guides were found",
    "no games found",
    "no game found",
    "couldn't find any guides",
    "couldn't find anything",
    "page could not be found",
)


class PSNProfilesFetchError(RuntimeError):
    """Raised when the browser fetch layer cannot return a PSNProfiles page."""


class PSNProfilesChallengeError(PSNProfilesFetchError):
    """Manual site verification is needed; callers must not retry around it."""


@dataclass
class BrowserResponse:
    text: str
    status_code: int = 200

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise PSNProfilesFetchError(
                f"PSNProfiles browser returned status {self.status_code}"
            )


def _trophy_page_is_complete(
    soup: BeautifulSoup,
    title: str,
    body: str,
) -> bool:
    """Wait for every trophy row declared by a PSNProfiles game page."""
    if "trophies" not in title:
        return True

    trophy_urls: set[str] = set()
    trophy_positions: set[int] = set()
    for anchor in soup.select('a[href*="/trophy/"]'):
        trophy_url = anchor.get("href", "").split("?", maxsplit=1)[0]
        link_match = _TROPHY_LINK.search(trophy_url)
        if link_match is None:
            continue
        trophy_urls.add(link_match.group(0).rstrip("/"))
        trophy_positions.add(int(link_match.group(1)))

    # Trophy URL positions are sequential and one-based. This catches partial
    # rarity-sorted DOMs even when the page omits a textual total.
    if trophy_positions and len(trophy_urls) < max(trophy_positions):
        return False

    declared_totals = [
        int(value.replace(",", ""))
        for value in _TROPHY_TOTAL.findall(body)
    ]
    if not declared_totals:
        return True
    # A page with DLC contains base-game, DLC-group, and platform totals. The
    # largest summary is the complete platform count. Restricting the match to
    # "Trophies • Points" avoids the unrelated lifetime "Trophies earned"
    # statistic in the page header.
    expected = max(declared_totals)
    return len(trophy_urls) >= expected


def _page_is_ready(html: str, requested_url: str | None = None) -> bool:
    """True once Cloudflare has yielded requested content or a terminal error."""
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(" ", strip=True).lower() if soup.title else ""
    if "just a moment" in title:
        return False

    body = soup.get_text(" ", strip=True).lower()
    if requested_url and urlsplit(requested_url).path.startswith("/trophies/"):
        game_id = urlsplit(requested_url).path.split("/")[2].split("-")[0]
        has_trophies = any(
            re.match(rf"/trophy/{re.escape(game_id)}(?:-|/)", anchor.get("href", ""))
            for anchor in soup.select('table.zebra a[href*="/trophy/"]')
        )
        if not has_trophies:
            return any(marker in body for marker in _ERROR_MARKERS)
    if soup.select_one("table.zebra"):
        return _trophy_page_is_complete(soup, title, body)

    if (
        soup.select_one("#user-bar .username")
        or soup.select_one('a[href*="/guide/"]')
        or "estimated trophy difficulty" in body
        or "approximate amount of time to platinum" in body
    ):
        return True

    return any(marker in body for marker in _ERROR_MARKERS)


def _navigation_matches(current: str, requested: str) -> bool:
    actual, wanted = urlsplit(current), urlsplit(requested)
    if (actual.hostname or "").removeprefix("www.") != (wanted.hostname or "").removeprefix("www."):
        return False
    if actual.path.rstrip("/") != wanted.path.rstrip("/"):
        return False
    actual_query = parse_qs(actual.query)
    return all(actual_query.get(key) == value for key, value in parse_qs(wanted.query).items())


class NodriverSession:
    """Small requests-like facade backed by one headed nodriver Chrome session.

    The same browser and cookies are reused for every page in one scrape, so
    Cloudflare is solved once rather than once per trophy-log page.
    """

    def __init__(self) -> None:
        self.headers: dict[str, str] = {}
        self._loop: asyncio.AbstractEventLoop | None = None
        self._browser = None
        self._nodriver = None
        self._lock_held = False
        self._closed = False

    def get(self, url: str, timeout: float | None = None) -> BrowserResponse:
        if self._closed:
            raise PSNProfilesFetchError("PSNProfiles browser session is closed")

        timeout = timeout or settings.psnprofiles_browser_timeout
        if not self._lock_held:
            _browser_profile_lock.acquire()
            self._lock_held = True

        try:
            if self._loop is None:
                import nodriver

                self._nodriver = nodriver
                self._loop = nodriver.loop()
            guarded = asyncio.wait_for(self._get(url, timeout), timeout=timeout + 15)
            return self._loop.run_until_complete(guarded)
        except TimeoutError as exc:
            raise PSNProfilesFetchError(
                f"Timed out after {timeout:g}s fetching {url} with the browser"
            ) from exc
        except PSNProfilesFetchError:
            raise
        except Exception as exc:
            raise PSNProfilesFetchError(
                f"Unable to fetch {url} with the PSNProfiles browser: {exc}"
            ) from exc

    async def _get(self, url: str, timeout: float) -> BrowserResponse:
        if self._browser is None:
            self._browser = await self._nodriver.start(
                headless=settings.psnprofiles_headless,
            )

        tab = await self._browser.get(url)
        deadline = time.monotonic() + timeout
        last_html = ""
        last_signature = None

        while time.monotonic() < deadline:
            state = await tab.evaluate(
                "({url: window.location.href, readyState: document.readyState})",
                return_by_value=True,
            )
            if not isinstance(state, dict) or not _navigation_matches(str(state.get("url", "")), url) or state.get("readyState") != "complete":
                last_signature = None
                await tab.sleep(0.5)
                continue
            last_html = await tab.get_content()
            soup = BeautifulSoup(last_html, "html.parser")
            title_text = soup.title.get_text(" ", strip=True).casefold() if soup.title else ""
            if any(marker in title_text for marker in ("just a moment", "attention required", "請稍候", "请稍候")):
                raise PSNProfilesChallengeError("PSNProfiles 需要手動完成網站驗證，請在瀏覽器完成後重試。")
            page_ready = _page_is_ready(last_html, url)
            if page_ready:
                # Compare meaningful page data rather than ads/animation markup.
                signature = (title_text, tuple(table.get_text(" ", strip=True)
                             for table in soup.select("table.zebra")),
                             tuple(a.get("href") for a in soup.select('a[href*="/trophy/"]')))
                if signature == last_signature:
                    return BrowserResponse(last_html)
                last_signature = signature
            else:
                last_signature = None
            # Trophy lists can lazy-render additional rows as the page scrolls.
            # Keep advancing by one viewport until the declared count and URL
            # positions are complete, then the next poll returns the full DOM.
            partial_soup = BeautifulSoup(last_html, "html.parser")
            partial_title = (
                partial_soup.title.get_text(" ", strip=True).lower()
                if partial_soup.title
                else ""
            )
            if (
                "trophies" in partial_title
                and partial_soup.select_one("table.zebra")
                and not page_ready
            ):
                await tab.scroll_down(100)
            await tab.sleep(1)

        title = BeautifulSoup(last_html, "html.parser").title
        title_text = title.get_text(" ", strip=True) if title else "unknown page"
        raise PSNProfilesFetchError(
            f"Timed out after {timeout:g}s waiting for PSNProfiles ({title_text})"
        )

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            if self._browser is not None:
                try:
                    browser = self._browser

                    async def shutdown_browser() -> None:
                        # nodriver.stop() only schedules aclose() and our
                        # synchronous wrapper used to close the loop before
                        # those tasks ran. Close every websocket explicitly so
                        # Chrome exits without pending-task error floods.
                        for tab in list(browser.tabs):
                            with suppress(Exception):
                                await tab.aclose()
                        with suppress(Exception):
                            await browser.aclose()

                        process = getattr(browser, "_process", None)
                        if process is not None and process.returncode is None:
                            process.terminate()
                            try:
                                await asyncio.wait_for(process.wait(), timeout=5)
                            except TimeoutError:
                                process.kill()
                                await process.wait()

                    if self._loop is not None and not self._loop.is_closed():
                        self._loop.run_until_complete(shutdown_browser())
                except Exception:
                    logger.debug("nodriver browser cleanup failed", exc_info=True)
        finally:
            self._browser = None
            if self._loop is not None and not self._loop.is_closed():
                # Let nodriver's scheduled websocket cleanup run before closing.
                try:
                    self._loop.run_until_complete(asyncio.sleep(0))
                except Exception:
                    logger.debug("nodriver loop cleanup failed", exc_info=True)
                try:
                    self._loop.close()
                except Exception:
                    logger.debug("nodriver loop close failed", exc_info=True)
            self._loop = None
            if self._lock_held:
                self._lock_held = False
                _browser_profile_lock.release()

    def __enter__(self) -> NodriverSession:
        return self

    def __exit__(self, *_args) -> None:
        self.close()


def create_session() -> NodriverSession:
    return NodriverSession()
