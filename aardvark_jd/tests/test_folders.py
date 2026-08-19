import os

import pytest

from aardvark_jd import db, folders


@pytest.fixture
def dbConn():
    conn = db.get_connection(":memory:")
    db.initialise_schema(conn)
    yield conn
    conn.close()


def test_next_area_decade_sequence_and_exhaustion(dbConn):
    seen = []
    for _ in range(9):
        decadeStart, decadeEnd = folders.next_area_decade(dbConn, "areas")
        seen.append(decadeStart)
        assert decadeEnd == decadeStart + 9
        db.insert_area(dbConn, "areas", decadeStart, decadeEnd, f"A{decadeStart}", "", "📁",
                        folders.area_folder_name("areas", decadeStart, decadeEnd, f"A{decadeStart}", "📁"), "/tmp/x")
    assert seen == list(range(10, 91, 10))
    with pytest.raises(folders.DomainExhaustedError):
        folders.next_area_decade(dbConn, "areas")


def test_next_area_decade_domains_are_independent(dbConn):
    db.insert_area(dbConn, "areas", 10, 19, "A", "", "📁", "x", "/tmp/x")
    decadeStart, _ = folders.next_area_decade(dbConn, "resources")
    assert decadeStart == 10


def test_next_category_number_sequence_and_exhaustion(dbConn):
    areaId = db.insert_area(dbConn, "areas", 10, 19, "Health", "", "🏥", "10-19 Health 🏥", "/tmp/h")
    area = db.get_area(dbConn, "areas", 10)
    seen = []
    for _ in range(9):
        acNumber = folders.next_category_number(dbConn, "areas", area)
        seen.append(acNumber)
        db.insert_category(dbConn, areaId, "areas", acNumber, f"C{acNumber}", "", "📁",
                            folders.category_folder_name("areas", acNumber, f"C{acNumber}", "📁"), "/tmp/h")
    assert seen == list(range(11, 20))
    with pytest.raises(folders.CategoryExhaustedError):
        folders.next_category_number(dbConn, "areas", area)


def test_next_id_number_sequence_and_exhaustion(dbConn):
    areaId = db.insert_area(dbConn, "areas", 10, 19, "Health", "", "🏥", "10-19 Health 🏥", "/tmp/h")
    catId = db.insert_category(dbConn, areaId, "areas", 11, "Doctors", "", "🩺", "11 Doctors 🩺", "/tmp/h/11")
    category = db.get_category(dbConn, "areas", 11)
    for expected in range(10, 100):
        itemNumber = folders.next_id_number(dbConn, "areas", category)
        assert itemNumber == expected
        db.insert_id(dbConn, catId, "areas", 11, itemNumber, f"I{itemNumber}", "",
                      folders.id_folder_name("areas", 11, itemNumber, f"I{itemNumber}"), "/tmp/h/11")
    with pytest.raises(folders.IdExhaustedError):
        folders.next_id_number(dbConn, "areas", category)


def test_area_folder_name_format():
    assert folders.area_folder_name("areas", 10, 19, "Health", "🏥") == "A10_19_health🏥"
    assert folders.area_folder_name("resources", 10, 19, "Health", "🏥") == "R10_19_health🏥"


def test_category_folder_name_format():
    assert folders.category_folder_name("areas", 11, "Doctors", "🩺") == "A11_doctors🩺"


def test_id_folder_name_has_no_emoji_by_default():
    name = folders.id_folder_name("areas", 11, 10, "Cardiologist")
    assert name == "A11.10_cardiologist"
    for character in name:
        assert ord(character) < 0x1F000, f"unexpected emoji-range character in ID folder name: {name!r}"


def test_id_folder_name_accepts_an_emoji_for_reserved_system_ids():
    name = folders.id_folder_name("areas", 11, 0, "Index", emoji="🗂️")
    assert name == "A11.00_index🗂️"


def test_slugify_lowercases_and_underscores_whitespace():
    assert folders.slugify("Health") == "health"
    assert folders.slugify("  Multi   Word Title ") == "multi_word_title"


def test_display_name_swaps_underscores_and_keeps_the_emoji():
    assert folders.display_name("01_INBOX📥") == "01 INBOX📥"
    assert folders.display_name("A.11_doctors🩺") == "A.11 doctors🩺"
    assert folders.display_name("A.11.10_cardiologist") == "A.11.10 cardiologist"


def test_display_name_keeps_a_decade_range_readable_as_a_hyphen():
    # the first underscore separates the range bounds, the rest are word gaps
    assert folders.display_name("A.10_19_health🏥") == "A.10-19 health🏥"
    assert folders.display_name("00_09_system⚙️") == "00-09 system⚙️"
    assert folders.display_name("R.20_29_home_admin📁") == "R.20-29 home admin📁"


def test_display_name_leaves_an_unnumbered_name_alone():
    assert folders.display_name("My Project🚀") == "My Project🚀"


def test_make_folder_is_idempotent(tmp_path):
    parent = str(tmp_path)
    path1 = folders.make_folder(parent, "10-19 Health 🏥")
    path2 = folders.make_folder(parent, "10-19 Health 🏥")
    assert path1 == path2
    assert os.path.isdir(path1)
