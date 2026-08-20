import pytest

from aardvark_jd import codes


def test_domain_letter():
    assert codes.domain_letter("areas") == "A"
    assert codes.domain_letter("resources") == "R"
    assert codes.domain_letter("projects") == "P"


def test_domain_letter_invalid():
    with pytest.raises(ValueError):
        codes.domain_letter("bogus")


@pytest.mark.parametrize("text,expected", [
    ("A10", 10),
    ("A10-19", 10),
    ("R20-29", 20),
    ("P30-39", 30),
    ("A.10", 10),
    ("A.10-19", 10),
    ("R.20-29", 20),
])
def test_parse_area_ref_valid(text, expected):
    assert codes.parse_area_ref(text) == expected


@pytest.mark.parametrize("text", ["9", "05", "11", "abc", "10-25", "", "10", "10-19", "Q10-19"])
def test_parse_area_ref_invalid(text):
    with pytest.raises(ValueError):
        codes.parse_area_ref(text)


@pytest.mark.parametrize("text,expected", [
    ("A11", 11),
    ("R23", 23),
    ("P31", 31),
    ("A.11", 11),
    ("R.23", 23),
])
def test_parse_category_ref_valid(text, expected):
    assert codes.parse_category_ref(text) == expected


@pytest.mark.parametrize("text", ["1", "abc", "10-19", "", "11", "A10-19", "Q11"])
def test_parse_category_ref_invalid(text):
    with pytest.raises(ValueError):
        codes.parse_category_ref(text)


def test_format_codes_round_trip():
    assert codes.format_area_code("areas", 10, 19) == "A10-19"
    assert codes.format_category_code("resources", 23) == "R23"
    assert codes.format_id_code("areas", 11, 1) == "A11.01"
    assert codes.format_id_code("projects", 11, 1) == "P11.01"


def test_domain_from_letter():
    assert codes.domain_from_letter("A") == "areas"
    assert codes.domain_from_letter("r") == "resources"
    assert codes.domain_from_letter("P") == "projects"
    # THE FULL DOMAIN WORD PASSES STRAIGHT THROUGH
    assert codes.domain_from_letter("resources") == "resources"


@pytest.mark.parametrize("text", ["Q", "", "AA", "10"])
def test_domain_from_letter_invalid(text):
    with pytest.raises(ValueError, match="not a valid domain letter"):
        codes.domain_from_letter(text)


def test_split_refs_return_the_domain_alongside_the_number():
    assert codes.split_area_ref("A10-19") == ("areas", 10)
    assert codes.split_area_ref("R.20") == ("resources", 20)
    assert codes.split_category_ref("P11") == ("projects", 11)


def test_domain_from_ref_covers_areas_and_categories_alike():
    assert codes.domain_from_ref("A11") == "areas"
    assert codes.domain_from_ref("P10-19") == "projects"
    with pytest.raises(ValueError):
        codes.domain_from_ref("root.areas")


def test_a_ref_contradicting_its_command_domain_is_rejected():
    with pytest.raises(ValueError, match="working in 'areas'"):
        codes.split_category_ref("R11", domain="areas")
    with pytest.raises(ValueError, match="working in 'projects'"):
        codes.parse_area_ref("A10-19", domain="projects")
    # A MATCHING LETTER IS FINE
    assert codes.parse_category_ref("A11", domain="areas") == 11


def test_is_jd_ref_separates_codes_from_system_folder_keys():
    assert codes.is_jd_ref("A10-19") is True
    assert codes.is_jd_ref("P11") is True
    assert codes.is_jd_ref("root.areas") is False
    assert codes.is_jd_ref("areas.system.02_llm") is False
    # THE LETTER IS MANDATORY, SO A BARE NUMBER IS NOT A JD REF
    assert codes.is_jd_ref("11") is False


@pytest.mark.parametrize("text,expected", [
    ("A10", True),
    ("A10-19", True),
    ("P20-29", True),
    ("A11", False),
    ("R23", False),
])
def test_parse_area_ref_is_area(text, expected):
    assert codes.parse_area_ref_is_area(text) is expected


# ---------------------------------------------------------------------- #
# ID references
# ---------------------------------------------------------------------- #

@pytest.mark.parametrize("ref", ["A11.10", "A.11.10", "R99.99", "P11.10"])
def test_is_id_ref_accepts_id_codes(ref):
    assert codes.is_id_ref(ref) is True


@pytest.mark.parametrize("ref", ["A11", "A10-19", "A", "root.areas", "11.10", ""])
def test_is_id_ref_rejects_everything_else(ref):
    assert codes.is_id_ref(ref) is False


def test_is_jd_ref_still_rejects_id_codes():
    """is_jd_ref answers 'area or category?', which is why is_id_ref exists"""
    assert codes.is_jd_ref("A11.10") is False


def test_split_id_ref_returns_its_three_parts():
    assert codes.split_id_ref("A11.10") == ("areas", 11, 10)
    assert codes.split_id_ref("P11.10") == ("projects", 11, 10)


def test_split_id_ref_accepts_the_legacy_dotted_form():
    assert codes.split_id_ref("A.11.10") == ("areas", 11, 10)


def test_split_id_ref_rejects_a_non_id_ref():
    with pytest.raises(ValueError):
        codes.split_id_ref("A11")


def test_split_id_ref_rejects_a_contradicting_domain():
    with pytest.raises(ValueError):
        codes.split_id_ref("A11.10", domain="projects")
