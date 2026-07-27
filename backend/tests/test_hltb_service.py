import sys
from types import SimpleNamespace

from app.core.cache import FileCache
from app.services import hltb_service


def test_get_hltb_times_caches_lookup(monkeypatch, tmp_path):
    calls = []

    def fake_search(game):
        calls.append(game)
        return {
            "game_name": "TUNIC",
            "main_story": 12.0,
            "main_extra": 16.0,
            "completionist": 22.0,
        }

    monkeypatch.setattr(hltb_service, "_search", fake_search)
    cache = FileCache(tmp_path)

    first = hltb_service.get_hltb_times("TUNIC", cache=cache)
    second = hltb_service.get_hltb_times("TUNIC", cache=cache)

    assert first == second
    assert calls == ["TUNIC"]


def test_search_selects_result_with_highest_similarity(monkeypatch):
    results = [
        SimpleNamespace(
            game_name="Tunic Soundtrack",
            main_story=0,
            main_extra=0,
            completionist=0,
            similarity=0.4,
        ),
        SimpleNamespace(
            game_name="TUNIC",
            main_story=12,
            main_extra=16,
            completionist=22,
            similarity=0.99,
        ),
    ]

    class FakeHowLongToBeat:
        def search(self, _game):
            return results

    monkeypatch.setitem(
        sys.modules,
        "howlongtobeatpy",
        SimpleNamespace(HowLongToBeat=FakeHowLongToBeat),
    )

    result = hltb_service._search("TUNIC")
    assert result is not None
    assert result["game_name"] == "TUNIC"
    assert result["completionist"] == 22
