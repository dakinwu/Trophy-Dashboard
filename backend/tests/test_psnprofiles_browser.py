import asyncio

from app.services.http import NodriverSession, _page_is_ready
from tests.conftest import load_fixture


def test_page_is_ready_for_current_profile_fixture():
    assert _page_is_ready(load_fixture("profile_summary.html"))


def test_page_is_ready_for_current_trophy_log_fixture():
    assert _page_is_ready(load_fixture("trophy_log_page.html"))


def test_page_is_ready_for_guide_search_fixture():
    assert _page_is_ready(load_fixture("psnprofiles_guide_search.html"))


def test_page_is_ready_for_guide_fixture():
    assert _page_is_ready(load_fixture("psnprofiles_guide.html"))


def test_page_is_not_ready_during_cloudflare_challenge():
    html = """
    <html>
      <head><title>Just a moment...</title></head>
      <body><div id="challenge-running">Verifying you are human</div></body>
    </html>
    """
    assert not _page_is_ready(html)


def test_trophy_page_waits_for_declared_trophy_count():
    partial = """
    <html>
      <head><title>Test Game Trophies - PSNProfiles</title></head>
      <body>
        <p>2 Trophies • 30 Points</p>
        <table class="zebra">
          <tr><td><a href="/trophy/123-test/1-first">First</a></td></tr>
        </table>
      </body>
    </html>
    """
    complete = partial.replace(
        "</table>",
        '<tr><td><a href="/trophy/123-test/2-second">Second</a></td></tr></table>',
    )

    assert not _page_is_ready(partial)
    assert _page_is_ready(complete)


def test_trophy_page_waits_for_missing_url_positions_without_text_total():
    partial = """
    <html>
      <head><title>Test Game Trophies - PSNProfiles</title></head>
      <body>
        <table class="zebra">
          <tr><td><a href="/trophy/123-test/1-first">First</a></td></tr>
          <tr><td><a href="/trophy/123-test/3-third">Third</a></td></tr>
        </table>
      </body>
    </html>
    """

    assert not _page_is_ready(partial)


def test_trophy_page_ignores_profile_wide_trophies_earned_total():
    html = """
    <html>
      <head><title>Test Game Trophies - PSNProfiles</title></head>
      <body>
        <p>5,206,242 TROPHIES EARNED</p>
        <p>1 Trophy • 15 Points</p>
        <table class="zebra">
          <tr><td><a href="/trophy/123-test/1-first">First</a></td></tr>
        </table>
      </body>
    </html>
    """

    assert _page_is_ready(html)


def test_trophy_page_uses_largest_total_when_dlc_is_present():
    partial = """
    <html>
      <head><title>Test Game Trophies - PSNProfiles</title></head>
      <body>
        <p>2 Trophies • 30 Points</p>
        <p>1 Trophy • 15 Points</p>
        <p>3 Trophies • 45 Points</p>
        <table class="zebra">
          <tr><td><a href="/trophy/123-test/1-first">First</a></td></tr>
          <tr><td><a href="/trophy/123-test/2-second">Second</a></td></tr>
        </table>
      </body>
    </html>
    """
    complete = partial.replace(
        "</table>",
        '<tr><td><a href="/trophy/123-test/3-third">Third</a></td></tr></table>',
    )

    assert not _page_is_ready(partial)
    assert _page_is_ready(complete)


def test_browser_scrolls_partial_trophy_page_until_complete():
    partial = """
    <html><head><title>Test Game Trophies - PSNProfiles</title></head>
    <body><p>2 Trophies • 30 Points</p><table class="zebra">
      <tr><td><a href="/trophy/123-test/1-first">First</a></td></tr>
    </table></body></html>
    """
    complete = partial.replace(
        "</table>",
        '<tr><td><a href="/trophy/123-test/2-second">Second</a></td></tr></table>',
    )

    class FakeTab:
        def __init__(self):
            self.pages = [partial, complete]
            self.reads = 0
            self.scrolls: list[int] = []

        async def get_content(self):
            page = self.pages[min(self.reads, 1)]
            self.reads += 1
            return page

        async def evaluate(self, *_args, **_kwargs):
            return {"url": "https://example.test/trophies/123", "readyState": "complete"}

        async def scroll_down(self, amount):
            self.scrolls.append(amount)

        async def sleep(self, _seconds):
            return None

    class FakeBrowser:
        def __init__(self, tab):
            self.tab = tab

        async def get(self, _url):
            return self.tab

    tab = FakeTab()
    session = NodriverSession()
    session._browser = FakeBrowser(tab)

    response = asyncio.run(session._get("https://example.test/trophies/123", 1))

    assert "Second" in response.text
    assert tab.scrolls == [100]


def test_page_is_ready_for_terminal_not_found_page():
    html = """
    <html>
      <head><title>PSNProfiles</title></head>
      <body><h1>Profile not found</h1></body>
    </html>
    """
    assert _page_is_ready(html)


def test_page_is_ready_for_empty_game_search():
    html = """
    <html>
      <head><title>Search • PSNProfiles.com</title></head>
      <body><h2>We couldn't find anything</h2></body>
    </html>
    """
    assert _page_is_ready(html)


def test_browser_reads_page_state_when_chrome_ignores_return_by_value():
    """Current Chrome ignores returnByValue alongside deep serialization, so
    nodriver hands back a RemoteObject for object results. Only primitive
    results (a JSON string) arrive intact."""
    import json
    from types import SimpleNamespace

    page = load_fixture("trophy_log_page.html")
    url = "https://psnprofiles.com/search/games?q=Outer+Wilds"

    class FakeTab:
        async def evaluate(self, expression, *_args, **_kwargs):
            state = {"url": url, "readyState": "complete"}
            if "JSON.stringify" in expression:
                return json.dumps(state)
            return SimpleNamespace(value=None, deep_serialized_value=object())

        async def get_content(self):
            return page

        async def scroll_down(self, _amount):
            return None

        async def sleep(self, _seconds):
            return None

    class FakeBrowser:
        async def get(self, _url):
            return FakeTab()

    session = NodriverSession()
    session._browser = FakeBrowser()

    response = asyncio.run(session._get(url, 2))

    assert response.text == page


def _challenge_then(page: str, challenge_reads: int, url: str):
    import json

    challenge = "<html><head><title>Just a moment...</title></head><body></body></html>"

    class FakeTab:
        def __init__(self):
            self.reads = 0

        async def evaluate(self, *_args, **_kwargs):
            return json.dumps({"url": url, "readyState": "complete"})

        async def get_content(self):
            self.reads += 1
            return challenge if self.reads <= challenge_reads else page

        async def scroll_down(self, _amount):
            return None

        async def sleep(self, _seconds):
            return None

    class FakeBrowser:
        async def get(self, _url):
            return FakeTab()

    session = NodriverSession()
    session._browser = FakeBrowser()
    return session


def test_browser_waits_for_cloudflare_to_clear_by_itself():
    page = load_fixture("trophy_log_page.html")
    url = "https://psnprofiles.com/search/games?q=Outer+Wilds"
    session = _challenge_then(page, challenge_reads=3, url=url)

    response = asyncio.run(session._get(url, 5))

    assert response.text == page


def test_browser_reports_a_challenge_that_never_clears(monkeypatch):
    import pytest

    from app.services import http
    from app.services.http import PSNProfilesChallengeError

    monkeypatch.setattr(http, "CHALLENGE_GRACE_SECONDS", 0.05)
    url = "https://psnprofiles.com/search/games?q=Outer+Wilds"
    session = _challenge_then("", challenge_reads=10**9, url=url)

    with pytest.raises(PSNProfilesChallengeError):
        asyncio.run(session._get(url, 5))
