import logging

import pytest
import yaml

from aardvark_jd import db, paths
from aardvark_jd.add_area import add_area
from aardvark_jd.add_category import add_category
from aardvark_jd.add_id import add_id
from aardvark_jd.initialiser import initialiser
from aardvark_jd.search import format_tree, tree

log = logging.getLogger("test_search_tree")
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
    # EXPLICIT EMOJI, SO THE RENDERED LABELS ARE EXACT RATHER THAN WHATEVER THE
    # SUGGESTER HAPPENS TO PICK FOR "HEALTH" ON THE DAY.
    add_area(log=log, dbConn=conn, domain="areas", title="Health", description="d1",
             chosenEmoji="🏥").get()
    add_category(log=log, dbConn=conn, domain="areas", areaRef="A10", title="Doctors",
                 description="d2", chosenEmoji="🩺").get()
    add_id(log=log, dbConn=conn, domain="areas", categoryRef="A11", title="Cardiologist", description="d3").get()
    add_id(log=log, dbConn=conn, domain="areas", categoryRef="A11", title="Dermatologist", description="d4").get()
    yield conn
    conn.close()


def test_the_whole_index_lists_all_three_domains(seeded):
    lines = tree(log=log, dbConn=seeded).get()
    joined = "\n".join(lines)
    assert "A areas" in joined
    assert "R resources" in joined
    assert "P projects" in joined


def test_the_whole_index_nests_area_category_and_ids(seeded):
    lines = tree(log=log, dbConn=seeded).get()
    joined = "\n".join(lines)
    assert "A10-19 🏥 Health" in joined
    assert "A11 🩺 Doctors" in joined
    assert "A11.10 Cardiologist" in joined
    assert "A11.11 Dermatologist" in joined


def test_an_area_and_category_carry_their_emoji_between_code_and_title(seeded):
    """*the emoji is the fastest way to recognise a branch, so it belongs in the listing*"""
    joined = "\n".join(tree(log=log, dbConn=seeded).get())
    assert "A10-19 🏥 Health" in joined
    assert "A11 🩺 Doctors" in joined


def test_an_id_line_carries_no_emoji(seeded):
    """*IDs have no emoji column, and their folders are never emoji-suffixed*"""
    joined = "\n".join(tree(log=log, dbConn=seeded).get())
    assert "A11.10 Cardiologist" in joined
    assert "A11.10 📁" not in joined


def test_a_domain_heading_carries_no_emoji(seeded):
    """*domain headings come from the code table, not from a row that owns an emoji*"""
    joined = "\n".join(tree(log=log, dbConn=seeded).get())
    assert "A areas" in joined
    assert "📁 areas" not in joined


def test_an_area_with_a_blank_emoji_falls_back_to_the_folder_emoji(seeded):
    """*a blank emoji is drifted data - flag it rather than silently closing the gap*"""
    seeded.execute("UPDATE areas SET emoji = '' WHERE decade_start = 10 AND domain = 'areas'")
    seeded.commit()

    joined = "\n".join(tree(log=log, dbConn=seeded).get())

    assert "A10-19 📁 Health" in joined


def test_a_category_with_a_blank_emoji_falls_back_to_the_folder_emoji(seeded):
    seeded.execute("UPDATE categories SET emoji = '' WHERE ac_number = 11 AND domain = 'areas'")
    seeded.commit()

    joined = "\n".join(tree(log=log, dbConn=seeded).get())

    assert "A11 📁 Doctors" in joined


def test_a_domain_letter_scopes_to_that_domain(seeded):
    joined = "\n".join(tree(log=log, dbConn=seeded, ref="A").get())
    assert "A10-19 🏥 Health" in joined
    assert "resources" not in joined


def test_an_area_ref_scopes_to_that_area(seeded):
    joined = "\n".join(tree(log=log, dbConn=seeded, ref="A10-19").get())
    assert "A10-19 🏥 Health" in joined
    assert "A11.10 Cardiologist" in joined
    assert "areas" not in joined


def test_a_category_ref_scopes_to_that_category(seeded):
    lines = tree(log=log, dbConn=seeded, ref="A11").get()
    joined = "\n".join(lines)
    assert "A11 🩺 Doctors" in joined
    assert "A10-19" not in joined


def test_reserved_system_ids_never_appear(seeded):
    """the .00-.09 scaffolding lives in system_folders, not ids"""
    joined = "\n".join(tree(log=log, dbConn=seeded).get())
    assert "A11.00" not in joined
    assert "A11.09" not in joined


def test_an_unknown_area_raises(seeded):
    with pytest.raises(ValueError):
        tree(log=log, dbConn=seeded, ref="A90-99").get()


def test_an_unknown_category_raises(seeded):
    with pytest.raises(ValueError):
        tree(log=log, dbConn=seeded, ref="A19").get()


def test_an_empty_domain_still_renders_its_heading(seeded):
    joined = "\n".join(tree(log=log, dbConn=seeded, ref="P").get())
    assert joined.strip() == "P projects"


def test_format_tree_draws_branch_connectors():
    nodes = [{
        "label": "parent", "path": "/p", "children": [
            {"label": "first", "path": "/p/a", "children": []},
            {"label": "last", "path": "/p/b", "children": []},
        ],
    }]
    assert format_tree(nodes) == [
        "└── parent",
        "    ├── first",
        "    └── last",
    ]


def test_the_tree_flags_a_drifted_mirror_at_the_top(seeded):
    """*sync runs unwatched, so the listing is where a failure has to be legible*"""
    db.record_sync_failure(seeded, "craft", "429 rate limited", "rate-limited")

    lines = tree(log=log, dbConn=seeded).get()

    assert lines[0].startswith("! craft is out of sync (rate-limited")
    assert lines[1] == ""


def test_the_tree_has_no_drift_header_when_every_mirror_is_healthy(seeded):
    db.record_sync_success(seeded, "craft")

    lines = tree(log=log, dbConn=seeded).get()

    assert not any(line.startswith("!") for line in lines)


def test_domain_sections_are_separated_by_a_blank_line(seeded):
    """*three flush-left headings ran together with no visual break between them*"""
    lines = tree(log=log, dbConn=seeded).get()

    headingIndexes = [i for i, line in enumerate(lines) if line and not line[0].isspace()
                      and "──" not in line and not line.startswith("!")]
    assert len(headingIndexes) == 3

    # EVERY HEADING BUT THE FIRST IS PRECEDED BY A BLANK LINE.
    for index in headingIndexes[1:]:
        assert lines[index - 1] == "", f"no blank line before {lines[index]!r}"

    # AND THE LISTING NEITHER STARTS NOR ENDS WITH ONE.
    assert lines[0] != ""
    assert lines[-1] != ""
