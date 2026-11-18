from app.core.cache import FileCache
from app.services.psnprofiles_guide_service import (
    _candidate_is_safe_match,
    get_psnprofiles_guide,
    parse_guide_page,
    parse_guide_search,
    psnprofiles_search_query,
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


def test_safe_title_match_rejects_shared_words_and_sequel_mismatches():
    unsafe_pairs = [
        ("Street Fighter V", "Street Fighter 6"),
        ("Mafia II Definitive Edition", "Dead Island Definitive Edition"),
        ("Assassin's Creed Origins", "Assassin's Creed II"),
        ("Alan Wake 2", "Alan Wake"),
        ("Journey", "Arcade Archives: Blue's Journey"),
        ("Destiny", "Gothic Murder: Adventure That Changes Destiny"),
        ("Evolve", "Radial-G: Racing Revolved"),
    ]

    assert all(
        not _candidate_is_safe_match(wanted, actual)
        for wanted, actual in unsafe_pairs
    )


def test_safe_title_match_allows_marketing_suffix_differences():
    safe_pairs = [
        ("Baldur's Gate 3", "Baldur's Gate III"),
        ("BioShock 2 Remastered", "BioShock 2"),
        ("Assassin's Creed III Remastered", "Assassin's Creed III"),
        ("Evil Dead", "Evil Dead: The Game"),
        ("Mafia Definitive Edition", "Mafia: Definitive Edition"),
    ]

    assert all(
        _candidate_is_safe_match(wanted, actual)
        for wanted, actual in safe_pairs
    )


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


def test_psnprofiles_search_query_removes_store_decorations():
    assert psnprofiles_search_query("KNACK™") == "KNACK"
    assert psnprofiles_search_query("Resident Evil Village (PS5)") == (
        "Resident Evil Village"
    )
    assert psnprofiles_search_query("Beyond: Two Souls™") == "Beyond Two Souls"


def test_guide_search_rejects_single_shared_word():
    html = """
    <article><h3>Memory Holder: Winds of Freedom Trophy Guide</h3>
      <a href="/guide/999-memory-holder-winds-of-freedom">Guide</a>
    </article>
    """
    assert parse_guide_search(html, "Where Winds Meet") is None


def test_safe_title_match_treats_roman_and_arabic_sequels_alike():
    from app.services.psnprofiles_guide_service import _candidate_score

    safe_pairs = [
        ("Final Fantasy 16", "Final Fantasy XVI"),
        ("Mafia 2", "Mafia II"),
        ("Street Fighter 5", "Street Fighter V"),
        ("Mafia 2 Definitive Edition", "Mafia II: Definitive Edition"),
        ("Final Fantasy XIV", "FINAL FANTASY XIV Online"),
    ]
    unsafe_pairs = [
        ("Final Fantasy XV", "Final Fantasy XVI"),
        ("Final Fantasy 15", "Final Fantasy XVI"),
        ("Mafia 3", "Mafia II"),
    ]

    assert all(_candidate_is_safe_match(w, a) for w, a in safe_pairs)
    assert not any(_candidate_is_safe_match(w, a) for w, a in unsafe_pairs)
    assert _candidate_score("Final Fantasy 16", "Final Fantasy XVI") == 1.0


def test_numeral_search_variants_swap_roman_and_arabic_numbers():
    from app.services.psnprofiles_guide_service import numeral_search_variants

    assert numeral_search_variants("Final Fantasy 16") == ["Final Fantasy XVI"]
    assert numeral_search_variants("Street Fighter V") == ["Street Fighter 5"]
    assert numeral_search_variants("Mafia II Definitive Edition") == [
        "Mafia 2 Definitive Edition"
    ]
    # Lone "I", sports years and plain titles are left alone.
    assert numeral_search_variants("I Am Setsuna") == []
    assert numeral_search_variants("F1 25") == []
    assert numeral_search_variants("NBA 2K25") == []
    assert numeral_search_variants("Journey") == []


def test_fallback_search_titles_try_numerals_then_shorter_titles():
    from app.services.psnprofiles_guide_service import fallback_search_titles

    assert fallback_search_titles(["Mafia 2 Definitive Edition"]) == [
        "Mafia 2 Definitive Edition",
        "Mafia II Definitive Edition",
        "Mafia 2",
        "Mafia II",
    ]
    assert fallback_search_titles(["Yakuza 5 Remastered", "Yakuza 5"]) == [
        "Yakuza 5 Remastered",
        "Yakuza 5",
        "Yakuza V Remastered",
        "Yakuza V",
    ]
    assert fallback_search_titles(["Journey"]) == ["Journey"]
    # Never strip a title down to nothing.
    assert fallback_search_titles(["Remastered"]) == ["Remastered"]
