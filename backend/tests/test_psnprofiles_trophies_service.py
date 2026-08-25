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
