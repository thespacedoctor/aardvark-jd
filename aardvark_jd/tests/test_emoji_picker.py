import pytest

from aardvark_jd import emoji_picker


def test_known_keyword_match():
    assert emoji_picker.pick_emoji("Hospital", "") == "🏥"


def test_no_match_falls_back():
    assert emoji_picker.pick_emoji("Xyzzyqwerty", "Blahblahblah") == emoji_picker.FALLBACK_EMOJI


def test_description_used_when_title_yields_nothing():
    picked = emoji_picker.pick_emoji("Xyzzyqwerty", "Hospital visits")
    assert picked == "🏥"


def test_title_takes_precedence_over_description():
    picked = emoji_picker.pick_emoji("Hospital", "Finance and money")
    assert picked == "🏥"


def test_case_insensitivity():
    assert emoji_picker.pick_emoji("HOSPITAL") == emoji_picker.pick_emoji("hospital")


def test_index_built_once(monkeypatch):
    emoji_picker._keywordIndex = None
    emoji_picker.pick_emoji("Hospital")
    firstIndex = emoji_picker._keywordIndex
    assert firstIndex is not None
    emoji_picker.pick_emoji("Finance")
    assert emoji_picker._keywordIndex is firstIndex


# ---------------------------------------------------------------- singularise


@pytest.mark.parametrize(
    "plural, singular",
    [("Films", "Film"), ("Links", "Link"), ("Flights", "Flight"), ("Recipes", "Recipe")],
)
def test_plural_title_matches_its_singular(plural, singular):
    assert emoji_picker.pick_emoji(plural) == emoji_picker.pick_emoji(singular)


def test_singularisation_rescues_titles_that_used_to_fall_back():
    for plural in ("Films", "Links", "Flights"):
        assert emoji_picker.pick_emoji(plural) != emoji_picker.FALLBACK_EMOJI


@pytest.mark.parametrize("plural", ["Books", "Glasses"])
def test_exact_match_wins_over_singularisation(plural):
    # these plurals are emoji keywords in their own right ("books" -> 📚), so
    # they must not be singularised away to a different emoji ("book" -> 📘)
    keywordIndex = emoji_picker._get_keyword_index()
    assert emoji_picker.pick_emoji(plural) == keywordIndex[plural.lower()]


def test_singular_forms_candidates():
    assert "story" in emoji_picker._singular_forms("stories")
    assert "box" in emoji_picker._singular_forms("boxes")
    assert "film" in emoji_picker._singular_forms("films")
    # a double-s word is not naively stripped
    assert emoji_picker._singular_forms("glass") == []
