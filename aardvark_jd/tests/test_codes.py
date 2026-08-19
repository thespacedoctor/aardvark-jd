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
    ("10", 10),
    ("10-19", 10),
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


@pytest.mark.parametrize("text", ["9", "05", "11", "abc", "10-25", ""])
def test_parse_area_ref_invalid(text):
    with pytest.raises(ValueError):
        codes.parse_area_ref(text)


@pytest.mark.parametrize("text,expected", [
    ("11", 11),
    ("A11", 11),
    ("R23", 23),
    ("P31", 31),
    ("A.11", 11),
    ("R.23", 23),
])
def test_parse_category_ref_valid(text, expected):
    assert codes.parse_category_ref(text) == expected


@pytest.mark.parametrize("text", ["1", "abc", "10-19", ""])
def test_parse_category_ref_invalid(text):
    with pytest.raises(ValueError):
        codes.parse_category_ref(text)


def test_format_codes_round_trip():
    assert codes.format_area_code("areas", 10, 19) == "A10-19"
    assert codes.format_category_code("resources", 23) == "R23"
    assert codes.format_id_code("areas", 11, 1) == "A11.01"
    assert codes.format_id_code("projects", 11, 1) == "P11.01"
