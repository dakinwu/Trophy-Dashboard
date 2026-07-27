from app.core.cache import FileCache
from app.services.psnprofiles_stats_service import (
    extract_psnprofiles_stats,
    get_psnprofiles_stats,
)
from tests.conftest import FakeSession, load_fixture


def test_extract_psnprofiles_stats_handles_world_and_country_rank():
    result = extract_psnprofiles_stats(
        {
            "Completion": "99.9%",
            "World Rank": "174309",
            "Country Rank": "4321",
        },
        "https://psnprofiles.com/TestUser",
    )
    assert result["world_rank"] == 174309
    assert result["country_rank"] == 4321
    assert result["country_label"] == "Country Rank"


def test_get_psnprofiles_stats_caches_profile_summary(tmp_path):
    session = FakeSession(summary_html=load_fixture("profile_summary.html"))
    cache = FileCache(tmp_path)

    first = get_psnprofiles_stats("TestUser", cache=cache, session=session)
    second = get_psnprofiles_stats("TestUser", cache=cache, session=session)

    assert first == second
    assert first is not None
    assert first["world_rank"] == 174309
    assert first["country_rank"] == 4321
