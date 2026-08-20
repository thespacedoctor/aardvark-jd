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
    add_area(log=log, dbConn=conn, domain="areas", title="Health", description="d1").get()
    add_category(log=log, dbConn=conn, domain="areas", areaRef="A10", title="Doctors", description="d2").get()
    add_id(log=log, dbConn=conn, domain="areas", categoryRef="A11", title="Cardiologist", description="d3").get()
    add_id(log=log, dbConn=conn, domain="areas", categoryRef="A11", title="Dermatologist", description="d4").get()
    yield conn
    conn.close()


def test_the_whole_index_lists_all_three_domains(seeded):
    lines = tree(log=log, dbConn=seeded).get()
    joined = "\n".join(lines)
    assert "A  areas" in joined
    assert "R  resources" in joined
    assert "P  projects" in joined


def test_the_whole_index_nests_area_category_and_ids(seeded):
    lines = tree(log=log, dbConn=seeded).get()
    joined = "\n".join(lines)
    assert "A10-19  Health" in joined
    assert "A11  Doctors" in joined
    assert "A11.10  Cardiologist" in joined
    assert "A11.11  Dermatologist" in joined


def test_a_domain_letter_scopes_to_that_domain(seeded):
    joined = "\n".join(tree(log=log, dbConn=seeded, ref="A").get())
    assert "A10-19  Health" in joined
    assert "resources" not in joined


def test_an_area_ref_scopes_to_that_area(seeded):
    joined = "\n".join(tree(log=log, dbConn=seeded, ref="A10-19").get())
    assert "A10-19  Health" in joined
    assert "A11.10  Cardiologist" in joined
    assert "areas" not in joined


def test_a_category_ref_scopes_to_that_category(seeded):
    lines = tree(log=log, dbConn=seeded, ref="A11").get()
    joined = "\n".join(lines)
    assert "A11  Doctors" in joined
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
    assert joined.strip() == "P  projects"


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
