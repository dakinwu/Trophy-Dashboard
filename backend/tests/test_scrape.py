import math

from tests.conftest import FakeSession, load_fixture
from app.services import psnprofiles


def _session_with(pages: int) -> FakeSession:
    log_html = load_fixture("trophy_log_page.html")
    return FakeSession(
        summary_html=load_fixture("profile_summary.html"),
        log_pages=[log_html] * pages,
    )


def test_fetch_summary_parses(monkeypatch):
    session = _session_with(0)
    summary = psnprofiles.fetch_summary(session, "https://psnprofiles.com/TestUser")
    assert summary is not None
    assert summary.total_trophies.total == 1234


def test_fetch_trophy_log_paginates_until_404(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)
    session = _session_with(3)
    seen_pages: list[int] = []
    log = psnprofiles.fetch_trophy_log(
        session,
        "https://psnprofiles.com/TestUser",
        on_progress=lambda page: seen_pages.append(page),
    )
    assert len(log) == 3            # one trophy per fixture page, 3 pages
    assert seen_pages == [1, 2, 3]


def test_fetch_trophy_log_respects_should_stop(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)
    session = _session_with(5)
    calls = {"n": 0}

    def should_stop() -> bool:
        calls["n"] += 1
        return calls["n"] > 2       # allow ~2 iterations then stop

    log = psnprofiles.fetch_trophy_log(
        session, "https://psnprofiles.com/TestUser", should_stop=should_stop
    )
    assert len(log) <= 2


def test_scrape_profile_reports_total_pages(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)
    session = _session_with(2)
    progress: list[tuple[int, int]] = []
    data = psnprofiles.scrape_profile(
        session, "TestUser", on_progress=lambda page, total: progress.append((page, total))
    )
    assert data is not None
    assert len(data.trophy_log) == 2
    expected_total = math.ceil(1234 / 50)
    assert progress[0] == (1, expected_total)


def test_scrape_profile_returns_none_for_missing(monkeypatch):
    session = FakeSession(summary_html="<html><body>nope</body></html>")
    assert psnprofiles.scrape_profile(session, "Ghost") is None
