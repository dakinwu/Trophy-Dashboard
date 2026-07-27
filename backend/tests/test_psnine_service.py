from app.core.cache import FileCache
from app.services.psnine_service import (
    build_psnine_url,
    get_psnine_title,
    parse_psnine_title,
)
from tests.conftest import FakeResponse, load_fixture


class FakePSNineSession:
    def __init__(self, html: str):
        self.html = html
        self.calls = 0

    def get(self, _url, **_kwargs):
        self.calls += 1
        return FakeResponse(self.html)


def test_parse_psnine_title_uses_text_link_not_image_link():
    title = parse_psnine_title(load_fixture("psnine_search.html"))
    assert title == "生化危机 村庄"


def test_build_psnine_url_uses_title_parameter():
    assert (
        build_psnine_url("仁王")
        == "https://www.psnine.com/psngame?title=%E4%BB%81%E7%8E%8B"
    )


def test_parse_psnine_title_rejects_english_only_results():
    html = '<a href="https://www.psnine.com/psngame/123">Some Game</a>'
    assert parse_psnine_title(html) is None


def test_get_psnine_title_caches_result(tmp_path):
    session = FakePSNineSession(load_fixture("psnine_search.html"))
    cache = FileCache(tmp_path)

    assert (
        get_psnine_title("Resident Evil Village", cache=cache, session=session)
        == "生化危机 村庄"
    )
    assert (
        get_psnine_title("Resident Evil Village", cache=cache, session=session)
        == "生化危机 村庄"
    )
    assert session.calls == 1
