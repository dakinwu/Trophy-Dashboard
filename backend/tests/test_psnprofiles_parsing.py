from app.models import TrophyCounts, ProfileSummary, Trophy, ProfileData
from tests.conftest import load_fixture
from app.services.psnprofiles import parse_profile_summary, parse_trophy_log_page


def test_models_construct_and_roundtrip():
    summary = ProfileSummary(
        username="TestUser",
        avatar_url="https://example.com/a.png",
        total_trophies=TrophyCounts(total=1234, platinum=10, gold=50, silver=300, bronze=874),
        stats={"Level": "42"},
    )
    trophy = Trophy(
        game="Test Game",
        icon_url="https://example.com/t.png",
        title="First Blood",
        timestamp="6th Jul 2024 10:11:23 pm",
        rarity_percent="2.5%",
        grade="Gold",
    )
    data = ProfileData(profile_summary=summary, trophy_log=[trophy])
    dumped = data.model_dump()
    restored = ProfileData.model_validate(dumped)
    assert restored.profile_summary.total_trophies.total == 1234
    assert restored.trophy_log[0].grade == "Gold"


def test_parse_profile_summary_extracts_fields():
    summary = parse_profile_summary(load_fixture("profile_summary.html"))
    assert summary is not None
    assert summary.username == "TestUser"
    assert summary.avatar_url == "https://example.com/avatar.png"
    assert summary.total_trophies.total == 1234
    assert summary.total_trophies.platinum == 10
    assert summary.stats["Level"] == "42"
    assert summary.stats["Completion"] == "99.9%"
    assert summary.stats["World Rank"] == "174309"


def test_parse_profile_summary_returns_none_on_garbage():
    assert parse_profile_summary("<html><body>nope</body></html>") is None


def test_parse_trophy_log_page_extracts_rows():
    trophies = parse_trophy_log_page(load_fixture("trophy_log_page.html"))
    assert len(trophies) == 1
    t = trophies[0]
    assert t.game == "Test Game"
    assert t.title == "First Blood"
    assert t.timestamp == "6th Jul 2024 10:11:23 pm"
    assert t.rarity_percent == "2.5%"
    assert t.grade == "Gold"


def test_parse_trophy_log_page_empty_when_no_table():
    assert parse_trophy_log_page("<html><body></body></html>") == []
