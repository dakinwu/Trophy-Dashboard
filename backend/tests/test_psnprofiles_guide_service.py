from app.core.cache import FileCache
from app.services.psnprofiles_guide_service import (
    get_psnprofiles_guide,
    parse_guide_page,
    parse_guide_search,
)
from tests.conftest import FakeResponse, load_fixture


class FakeGuideSession:
    def __init__(self):
        self.calls: list[str] = []

    def get(self, url, **_kwargs):
        self.calls.append(url)
        if "/search/guides" in url:
            return FakeResponse(load_fixture("psnprofiles_guide_search.html"))
        return FakeResponse(load_fixture("psnprofiles_guide.html"))


def test_parse_guide_search_selects_best_title_match():
    result = parse_guide_search(
        load_fixture("psnprofiles_guide_search.html"),
        "God of War",
    )
    assert result == {
        "title": "God of War Trophy Guide",
        "guide_url": "https://psnprofiles.com/guide/1234-god-of-war-trophy-guide",
    }


def test_parse_guide_page_extracts_difficulty_and_time():
    result = parse_guide_page(
        load_fixture("psnprofiles_guide.html"),
        "https://psnprofiles.com/guide/1234-god-of-war-trophy-guide",
    )
    assert result["difficulty"] == "4/10"
    assert result["platinum_time"] == "40-50 hours"


def test_get_psnprofiles_guide_caches_success(tmp_path):
    session = FakeGuideSession()
    cache = FileCache(tmp_path)

    first = get_psnprofiles_guide("God of War", cache=cache, session=session)
    second = get_psnprofiles_guide("God of War", cache=cache, session=session)

    assert first == second
    assert first is not None
    assert first["difficulty"] == "4/10"
    assert len(session.calls) == 2
