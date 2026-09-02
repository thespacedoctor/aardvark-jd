import pytest

from aardvark_jd import emoji_picker, labels


def _area(decadeStart=10, decadeEnd=19, emoji="🏥", title="Health"):
    return {"decade_start": decadeStart, "decade_end": decadeEnd, "emoji": emoji, "title": title}


def _category(acNumber=11, emoji="🩺", title="Doctors"):
    return {"ac_number": acNumber, "emoji": emoji, "title": title}


def _id(acNumber=11, itemNumber=10, title="Cardiologist"):
    return {"ac_number": acNumber, "item_number": itemNumber, "title": title}


def test_an_area_label_puts_its_emoji_between_the_code_and_the_title():
    assert labels.area_label("areas", _area()) == "A10-19 🏥 Health"


def test_a_category_label_puts_its_emoji_between_the_code_and_the_title():
    assert labels.category_label("areas", _category()) == "A11 🩺 Doctors"


def test_an_area_with_no_stored_emoji_falls_back_to_the_folder_emoji():
    """*a blank emoji is missing data, not an absence of the concept, so it is flagged*"""
    assert labels.area_label("areas", _area(emoji="")) == "A10-19 📁 Health"


def test_a_category_with_no_stored_emoji_falls_back_to_the_folder_emoji():
    assert labels.category_label("areas", _category(emoji="")) == "A11 📁 Doctors"


def test_the_fallback_is_the_one_the_emoji_picker_already_uses():
    assert labels.area_label("areas", _area(emoji="")).split()[1] == emoji_picker.FALLBACK_EMOJI


def test_an_id_label_carries_no_emoji():
    """*IDs have no emoji column and their folders are never emoji-suffixed*"""
    assert labels.id_label("areas", _id()) == "A11.10 Cardiologist"


def test_a_domain_label_is_its_letter_and_name():
    assert labels.domain_label("areas") == "A areas"
    assert labels.domain_label("resources") == "R resources"
    assert labels.domain_label("projects") == "P projects"


def test_labels_use_single_spaces_throughout():
    assert "  " not in labels.area_label("areas", _area())
    assert "  " not in labels.category_label("areas", _category())
    assert "  " not in labels.id_label("areas", _id())
    assert "  " not in labels.domain_label("areas")


def test_labels_honour_the_domain_letter():
    assert labels.area_label("projects", _area()).startswith("P10-19")
    assert labels.category_label("resources", _category()).startswith("R11")
    assert labels.id_label("projects", _id()).startswith("P11.10")


@pytest.mark.parametrize("entityType, code, emoji, expected", [
    ("area", "A10-19", "🏥", "A10-19 🏥 Health"),
    ("category", "A11", "🩺", "A11 🩺 Health"),
    ("area", "A10-19", "", "A10-19 📁 Health"),
    ("area", "A10-19", None, "A10-19 📁 Health"),
    ("id", "A11.10", None, "A11.10 Health"),
])
def test_a_search_result_label_is_built_from_the_result_row(entityType, code, emoji, expected):
    """*search rows carry a pre-formatted code, so the label is built from that rather than re-derived*"""
    row = {"entity_type": entityType, "code": code, "title": "Health"}
    if emoji is not None:
        row["emoji"] = emoji
    assert labels.result_label(row) == expected


def test_a_search_result_with_no_code_is_still_labelled():
    row = {"entity_type": "id", "code": None, "title": "Health"}
    assert labels.result_label(row) == "Health"
