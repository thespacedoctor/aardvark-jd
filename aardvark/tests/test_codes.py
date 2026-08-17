import pytest

from aardvark import codes


def test_domain_letter():
    assert codes.domain_letter("areas") == "A"
    assert codes.domain_letter("resources") == "R"


def test_domain_letter_invalid():
    with pytest.raises(ValueError):
        codes.domain_letter("projects")


@pytest.mark.parametrize("text,expected", [
    ("10", 10),
    ("10-19", 10),
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
    assert codes.format_area_code("areas", 10, 19) == "A.10-19"
    assert codes.format_category_code("resources", 23) == "R.23"
    assert codes.format_id_code("areas", 11, 1) == "A.11.01"
