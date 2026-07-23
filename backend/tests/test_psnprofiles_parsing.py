from app.models import TrophyCounts, ProfileSummary, Trophy, ProfileData


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
