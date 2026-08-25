from app.services.autopop_catalog import get_autopop_info


def test_catalog_matches_localized_nioh_2_title():
    info = get_autopop_info("仁王２ Remastered")

    assert info is not None
    assert info.status == "partial"


def test_catalog_matches_localized_scarlet_nexus_title():
    info = get_autopop_info("緋紅結繫")

    assert info is not None
    assert info.status == "full"


def test_catalog_does_not_guess_unlisted_game():
    assert get_autopop_info("Entirely Unlisted Game") is None
