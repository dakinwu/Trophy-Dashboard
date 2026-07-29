from app.core.cache import FileCache
from app.services.psnprofiles_trophies_service import (
    get_psnprofiles_trophies,
    parse_game_search,
    parse_trophy_page,
)
from tests.conftest import FakeResponse, load_fixture


class FakeTrophySession:
    def __init__(self):
        self.calls: list[str] = []

    def get(self, url, **_kwargs):
        self.calls.append(url)
        if "/search/games" in url:
            return FakeResponse(load_fixture("psnprofiles_game_search.html"))
        return FakeResponse(load_fixture("psnprofiles_trophy_page.html"))


def test_parse_game_search_uses_requested_platform():
    result = parse_game_search(
        load_fixture("psnprofiles_game_search.html"),
        "Resident Evil Village",
        "PS5",
    )
    assert result == {
        "title": "Resident Evil Village",
        "game_url": "https://psnprofiles.com/trophies/201-resident-evil-village",
        "platform": "PS5",
    }


def test_parse_trophy_page_extracts_rarity():
    result = parse_trophy_page(load_fixture("psnprofiles_trophy_page.html"))
    assert len(result) == 3
    assert result[0]["trophy_id"] == 0
    assert result[0]["title"] == "Ethan Winters"
    assert result[0]["psnprofiles_rarity_percent"] == "45.67%"
    assert result[0]["rarity_percentages"] == ["45.67%", "18.42%"]
    assert result[0]["rarity_label"] == "Uncommon"
    assert result[1]["trophy_id"] == 1
    assert result[2]["trophy_id"] == 52
    assert result[2]["title"] == "Supreme Teen"
    assert result[2]["psnprofiles_rarity_percent"] == "12.34%"


def test_get_psnprofiles_trophies_caches_success(tmp_path):
    session = FakeTrophySession()
    cache = FileCache(tmp_path)

    first = get_psnprofiles_trophies(
        "Resident Evil Village",
        "PS5",
        cache=cache,
        session=session,
    )
    second = get_psnprofiles_trophies(
        "Resident Evil Village",
        "PS5",
        cache=cache,
        session=session,
    )

    assert first == second
    assert first is not None
    assert len(first["trophies"]) == 3
    assert len(session.calls) == 2
    assert session.calls[1] == (
        "https://psnprofiles.com/trophies/201-resident-evil-village"
        "?order=rarity"
    )
