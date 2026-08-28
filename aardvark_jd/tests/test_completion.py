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
    assert "search" in _values(completion.candidates(["av"], 1))


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
    values = _values(completion.candidates(["av", "search", "", "-s", seeded], 2))
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
