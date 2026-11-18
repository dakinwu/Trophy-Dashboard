import hashlib

from app.core.cache import FileCache
from app.services.psnprofiles_trophies_service import (
    get_psnprofiles_trophies,
    parse_game_search,
    parse_game_stats,
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


def test_parse_game_stats_reads_tracked_player_signals():
    result = parse_game_stats(load_fixture("psnprofiles_trophy_page.html"))

    assert result == {
        "owners": 12_345,
        "average_completion": 67.8,
        "platinum_achievers": 5_000,
        "platinum_rate": 40.5,
    }


def test_parse_game_search_rejects_loose_psnprofiles_results():
    html = """
    <div><span class="title">From Two Sides</span><span>PS4</span>
      <a href="/trophies/999-from-two-sides" title="From Two Sides">Open</a>
    </div>
    <div><span class="title">Memory Holder: Winds of Freedom</span><span>PS5</span>
      <a href="/trophies/998-memory-holder-winds-of-freedom"
         title="Memory Holder: Winds of Freedom">Open</a>
    </div>
    """
    assert parse_game_search(html, "Beyond Two Souls", "PS4") is None
    assert parse_game_search(html, "Where Winds Meet", "PS5") is None


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
    assert first["owners"] == 12_345
    assert first["average_completion"] == 67.8
    assert len(session.calls) == 2
    assert session.calls[1] == (
        "https://psnprofiles.com/trophies/201-resident-evil-village"
        "?order=rarity"
    )


def test_get_psnprofiles_trophies_uses_clean_search_title(tmp_path):
    session = FakeTrophySession()

    result = get_psnprofiles_trophies(
        "Resident Evil Village™ (PS5)",
        "PS5",
        cache=FileCache(tmp_path),
        session=session,
    )

    assert result is not None
    assert session.calls[0] == (
        "https://psnprofiles.com/search/games?q=Resident+Evil+Village"
    )


def test_cache_only_miss_does_not_create_session(tmp_path):
    result = get_psnprofiles_trophies(
        "Uncached Game",
        "PS5",
        cache=FileCache(tmp_path),
        cache_only=True,
    )

    assert result is None


def test_cache_only_migrates_valid_legacy_punctuation_key(tmp_path):
    cache = FileCache(tmp_path)
    legacy_seed = "beyond: two souls:PS4"
    legacy_digest = hashlib.sha256(legacy_seed.encode("utf-8")).hexdigest()
    legacy_key = f"psnprofiles_trophies_v7/{legacy_digest}"
    cached = {
        "title": "Beyond: Two Souls",
        "platform": "PS4",
        "game_url": "https://psnprofiles.com/trophies/2856-beyond-two-souls",
        "trophies": [{"trophy_id": 0, "title": "BEYOND: TWO SOULS"}],
    }
    cache.save(legacy_key, cached)

    result = get_psnprofiles_trophies(
        "Beyond Two Souls",
        "PS4",
        search_aliases=["Beyond: Two Souls™"],
        cache=cache,
        cache_only=True,
    )

    current_seed = "beyond two souls:PS4"
    current_digest = hashlib.sha256(current_seed.encode("utf-8")).hexdigest()
    current_key = f"psnprofiles_trophies_v7/{current_digest}"
    assert result == cached
    assert cache.load(current_key, 60) == cached
    assert cache.load(legacy_key, 60) is None


def test_parse_game_search_prefers_most_owned_of_equal_regional_lists():
    # PSNProfiles lists regional trophy lists separately; the first result can
    # be a tiny regional list (here JP, 204 owners) rather than the main one.
    html = """
    <table class="zebra">
      <tr><td><a class="title" href="/trophies/10873-bioshock-2">BioShock 2</a>
        <span>• JP</span><span class="platform">PS4</span>
        <span>56.12% AVERAGE</span><span>204 OWNERS</span></td></tr>
      <tr><td><a class="title" href="/trophies/5286-bioshock-2">BioShock 2</a>
        <span class="platform">PS4</span>
        <span>39.05% AVERAGE</span><span>158,620 OWNERS</span></td></tr>
      <tr><td><a class="title" href="/trophies/223-bioshock-2">BioShock 2</a>
        <span class="platform">PS3</span>
        <span>25.36% AVERAGE</span><span>318,632 OWNERS</span></td></tr>
      <tr><td><a class="title" href="/trophies/10871-bioshock-2">BioShock 2</a>
        <span>• EU</span><span class="platform">PS4</span>
        <span>32.38% AVERAGE</span><span>4,377 OWNERS</span></td></tr>
    </table>
    """
    result = parse_game_search(html, "BioShock 2", "PS4")

    assert result is not None
    assert result["game_url"] == "https://psnprofiles.com/trophies/5286-bioshock-2"


def test_failed_search_retries_with_roman_numeral_title(tmp_path):
    no_match = """
    <table class="zebra"><tr><td>
      <a class="title" href="/trophies/1-final-fantasy-x-x-2-hd">Final Fantasy X / X-2 HD</a>
      <span>PS4</span><span>100 OWNERS</span></td></tr></table>
    """
    roman_match = """
    <table class="zebra"><tr><td>
      <a class="title" href="/trophies/21321-final-fantasy-xvi">Final Fantasy XVI</a>
      <span>PS5</span><span>183,817 OWNERS</span></td></tr></table>
    """

    class Session:
        def __init__(self):
            self.calls: list[str] = []

        def get(self, url, **_kwargs):
            self.calls.append(url)
            if "/search/games" in url:
                return FakeResponse(roman_match if "XVI" in url else no_match)
            return FakeResponse(load_fixture("psnprofiles_trophy_page.html"))

    session = Session()
    result = get_psnprofiles_trophies(
        "Final Fantasy 16", "PS5", cache=FileCache(tmp_path), session=session
    )

    assert result is not None
    assert result["title"] == "Final Fantasy XVI"
    assert "https://psnprofiles.com/search/games?q=Final+Fantasy+XVI" in session.calls


def test_failed_search_retries_without_edition_suffix(tmp_path):
    unrelated = """
    <table class="zebra"><tr><td>
      <a class="title" href="/trophies/4671-dead-island-definitive-edition">Dead Island: Definitive Edition</a>
      <span>PS4</span><span>226,481 OWNERS</span></td></tr></table>
    """
    mafia = """
    <table class="zebra">
      <tr><td><a class="title" href="/trophies/372-mafia-ii">Mafia II</a>
        <span>PS3</span><span>345,968 OWNERS</span></td></tr>
      <tr><td><a class="title" href="/trophies/10846-mafia-ii">Mafia II</a>
        <span>PS4</span><span>154,329 OWNERS</span></td></tr>
    </table>
    """

    class Session:
        def __init__(self):
            self.queries: list[str] = []

        def get(self, url, **_kwargs):
            if "/search/games" in url:
                query = url.split("q=", 1)[1]
                self.queries.append(query)
                return FakeResponse(mafia if query == "Mafia+II" else unrelated)
            return FakeResponse(load_fixture("psnprofiles_trophy_page.html"))

    session = Session()
    result = get_psnprofiles_trophies(
        "Mafia 2 Definitive Edition", "PS4", cache=FileCache(tmp_path), session=session
    )

    assert result is not None
    assert result["game_url"] == "https://psnprofiles.com/trophies/10846-mafia-ii"
    assert list(dict.fromkeys(session.queries)) == [
        "Mafia+2+Definitive+Edition",
        "Mafia+II+Definitive+Edition",
        "Mafia+2",
        "Mafia+II",
    ]
