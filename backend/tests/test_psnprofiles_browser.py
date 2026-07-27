from app.services.http import _page_is_ready
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


def test_page_is_ready_for_terminal_not_found_page():
    html = """
    <html>
      <head><title>PSNProfiles</title></head>
      <body><h1>Profile not found</h1></body>
    </html>
    """
    assert _page_is_ready(html)
