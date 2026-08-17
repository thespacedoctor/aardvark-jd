from aardvark import emoji_picker


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
