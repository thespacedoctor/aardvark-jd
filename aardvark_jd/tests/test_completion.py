import logging

import pytest
import yaml

from aardvark_jd import completion, db, paths
from aardvark_jd.add_area import add_area
from aardvark_jd.add_category import add_category
from aardvark_jd.add_id import add_id
from aardvark_jd.initialiser import initialiser

log = logging.getLogger("test_completion")
log.addHandler(logging.NullHandler())


@pytest.fixture
def seeded(tmp_path):
    settingsPath = str(tmp_path / "settings.yaml")
    with open(settingsPath, "w") as stream:
        yaml.safe_dump({"version": 1, "system": {"name": None, "root_path": None}}, stream)
    rootPath = initialiser(
        log=log, systemName="Test", parentPath=str(tmp_path), pathToSettingsFile=settingsPath
    ).get()
    conn = db.get_connection(paths.find_db_path(rootPath))
    add_area(log=log, dbConn=conn, domain="areas", title="Health", description="d1").get()
    add_category(log=log, dbConn=conn, domain="areas", areaRef="A10", title="Doctors", description="d2").get()
    add_id(log=log, dbConn=conn, domain="areas", categoryRef="A11", title="Cardiologist", description="d3").get()
    conn.close()
    yield settingsPath


def _values(pairs):
    return [value for value, _description in pairs]


def test_first_word_completes_subcommands():
    assert "add_area" in _values(completion.candidates(["av", ""], 1))


def test_subcommands_are_filtered_by_prefix():
    values = _values(completion.candidates(["av", "add_c"], 1))
    assert values == ["add_category"]


def test_bare_program_name_completes_subcommands():
    assert "fd" in _values(completion.candidates(["av"], 1))


def test_domain_letters_complete_for_add_area():
    assert _values(completion.candidates(["av", "add_area", ""], 2)) == ["A", "R", "P"]


def test_shell_names_complete_for_completion():
    assert _values(completion.candidates(["av", "completion", ""], 2)) == ["bash", "zsh"]


def test_areas_complete_for_add_category(seeded):
    values = _values(completion.candidates(["av", "add_category", "", "-s", seeded], 2))
    assert values == ["A10-19"]


def test_completion_reader_waits_out_a_concurrent_write(seeded):
    """*the read-only completion connection sets `busy_timeout`, so a TAB press waits rather than failing*"""
    busyTimeout = completion._with_connection(
        lambda conn: conn.execute("PRAGMA busy_timeout").fetchone()[0],
        ["av", "add_category", "", "-s", seeded],
    )
    assert busyTimeout == 5000


def test_categories_complete_for_add_id(seeded):
    values = _values(completion.candidates(["av", "add_id", "", "-s", seeded], 2))
    assert values == ["A11"]


def test_refs_for_archive_include_every_level(seeded):
    values = _values(completion.candidates(["av", "archive", "", "-s", seeded], 2))
    assert values == ["A10-19", "A11", "A11.10"]


def test_refs_are_filtered_by_prefix(seeded):
    values = _values(completion.candidates(["av", "archive", "A11.", "-s", seeded], 2))
    assert values == ["A11.10"]


def test_search_also_offers_bare_domain_letters(seeded):
    values = _values(completion.candidates(["av", "fd", "", "-s", seeded], 2))
    assert values[:3] == ["A", "R", "P"]


def test_flags_complete_when_the_word_starts_with_a_dash():
    values = _values(completion.candidates(["av", "add_area", "A", "t", "d", "-"], 5))
    assert "--emoji" in values


def test_a_flag_value_slot_offers_nothing_so_the_shell_falls_back():
    assert completion.candidates(["av", "add_id", "-s", ""], 3) == []


def test_positional_slots_skip_flags_and_their_values(seeded):
    """`add_category -s x.yaml <TAB>` is still the FIRST positional, not the third"""
    values = _values(completion.candidates(["av", "add_category", "-s", seeded, ""], 4))
    assert values == ["A10-19"]


def test_unknown_subcommand_offers_nothing():
    assert completion.candidates(["av", "no_such_command", ""], 2) == []


def test_a_missing_system_is_silent_rather_than_an_error(tmp_path):
    emptySettings = str(tmp_path / "empty.yaml")
    with open(emptySettings, "w") as stream:
        yaml.safe_dump({"version": 1}, stream)
    assert completion.candidates(["av", "add_category", "", "-s", emptySettings], 2) == []


def test_emit_prints_value_and_description(capsys):
    completion.emit(["1", "av", "add_c"])
    out = capsys.readouterr().out
    assert out.startswith("add_category\t")


def test_emit_never_raises_on_garbage(capsys):
    completion.emit(["not-a-number"])
    completion.emit([])
    assert capsys.readouterr().out == ""


def test_settings_path_is_read_from_the_command_line(seeded):
    assert completion._settings_path_from(["av", "add_id", "-s", seeded]) == seeded
    assert completion._settings_path_from(["av", "add_id"]).endswith("aardvark.yaml")


@pytest.mark.parametrize("shell", ["bash", "zsh"])
def test_script_is_returned_for_each_supported_shell(shell):
    text = completion.script(shell)
    assert "__complete" in text
    assert "aardvark" in text and " av" in text


def test_script_rejects_an_unknown_shell():
    with pytest.raises(ValueError):
        completion.script("fish")


@pytest.fixture
def seededAllDomains(tmp_path):
    """*an area and category in each of the three domains*"""
    settingsPath = str(tmp_path / "settings.yaml")
    with open(settingsPath, "w") as stream:
        yaml.safe_dump({"version": 1, "system": {"name": None, "root_path": None}}, stream)
    rootPath = initialiser(
        log=log, systemName="Test", parentPath=str(tmp_path), pathToSettingsFile=settingsPath
    ).get()
    conn = db.get_connection(paths.find_db_path(rootPath))
    for domain, letter in (("areas", "A"), ("resources", "R"), ("projects", "P")):
        add_area(log=log, dbConn=conn, domain=domain, title="Things", description="d").get()
        add_category(
            log=log, dbConn=conn, domain=domain, areaRef=f"{letter}10",
            title="Stuff", description="d",
        ).get()
    conn.close()
    yield settingsPath


def test_add_project_completes_only_project_categories(seededAllDomains):
    """*a project always lands in the projects domain, so offering `A11` proposes a failure*"""
    values = _values(completion.candidates(["av", "add_project", "", "-s", seededAllDomains], 2))

    assert values == ["P11"]


def test_add_id_still_completes_categories_in_every_domain(seededAllDomains):
    """*an ID can be added to any domain's category - this one must not be narrowed*"""
    values = _values(completion.candidates(["av", "add_id", "", "-s", seededAllDomains], 2))

    assert sorted(values) == ["A11", "P11", "R11"]


def test_add_category_still_completes_areas_in_every_domain(seededAllDomains):
    """*`add_category` derives its domain from the area ref, so every area is valid*"""
    values = _values(completion.candidates(["av", "add_category", "", "-s", seededAllDomains], 2))

    assert sorted(values) == ["A10-19", "P10-19", "R10-19"]


def test_area_and_category_completions_show_their_emoji(seeded):
    """*the emoji is what makes a folder recognisable at a glance in the picker*"""
    areaPairs = completion.candidates(["av", "add_category", "", "-s", seeded], 2)
    areaDescription = dict(areaPairs)["A10-19"]

    categoryPairs = completion.candidates(["av", "add_id", "", "-s", seeded], 2)
    categoryDescription = dict(categoryPairs)["A11"]

    # THE VALUE STAYS THE BARE CODE - ONLY THE DESCRIPTION GAINS THE EMOJI.
    assert areaDescription.endswith("Health")
    assert areaDescription != "Health"
    assert categoryDescription.endswith("Doctors")
    assert categoryDescription != "Doctors"


def test_id_completions_are_unchanged_because_ids_carry_no_emoji(seeded):
    """*`ids` has no emoji column - an ID's folder name never carries one*"""
    pairs = completion.candidates(["av", "archive", "A11.", "-s", seeded], 2)

    assert dict(pairs)["A11.10"] == "Cardiologist"
