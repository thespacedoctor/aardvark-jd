import logging
import os
import zipfile

import pytest
import yaml

from aardvark_jd import db, paths
from aardvark_jd.add_area import add_area
from aardvark_jd.add_category import add_category
from aardvark_jd.initialiser import initialiser
from aardvark_jd.add_project import add_project

log = logging.getLogger("test_add_project")
log.addHandler(logging.NullHandler())


@pytest.fixture
def dbConnWithProjectCategory(tmp_path):
    settingsPath = str(tmp_path / "settings.yaml")
    with open(settingsPath, "w") as stream:
        yaml.safe_dump({"version": 1, "system": {"name": None, "root_path": None}}, stream)
    rootPath = initialiser(
        log=log, systemName="Test", parentPath=str(tmp_path), pathToSettingsFile=settingsPath
    ).get()
    conn = db.get_connection(paths.find_db_path(rootPath))
    add_area(log=log, dbConn=conn, domain="projects", title="Launches", description="").get()
    add_category(log=log, dbConn=conn, domain="projects", areaRef="P10", title="Website", description="").get()
    templatesFolder = paths.resolve(conn, "projects.11.04_templates")
    yield conn, templatesFolder
    conn.close()


def test_blank_scaffold(dbConnWithProjectCategory):
    conn, _ = dbConnWithProjectCategory
    code, title, folderPath, templateUsed = add_project(
        log=log, dbConn=conn, categoryRef="P11", templateName="blank", projectTitle="My Project"
    ).get()

    assert code == "P11.10"
    assert title == "My Project"
    assert templateUsed == "blank"
    assert os.path.basename(folderPath) == "P11.10_my_project"
    assert os.path.isfile(f"{folderPath}/README.md")
    assert os.path.isdir(f"{folderPath}/input")
    assert os.path.isdir(f"{folderPath}/output")

    row = conn.execute("SELECT * FROM ids WHERE title = ?", ("My Project",)).fetchone()
    assert row is not None
    assert row["domain"] == "projects"
    assert row["folder_name"] == "P11.10_my_project"


def test_zip_template_extraction(dbConnWithProjectCategory, tmp_path):
    conn, templatesFolder = dbConnWithProjectCategory

    customZipPath = f"{templatesFolder}/custom.zip"
    with zipfile.ZipFile(customZipPath, "w") as zipHandle:
        zipHandle.writestr("NOTES.md", "hello")

    _code, _title, folderPath, templateUsed = add_project(
        log=log, dbConn=conn, categoryRef="P11", templateName="custom", projectTitle="Custom Project"
    ).get()

    assert templateUsed == "custom.zip"
    assert os.path.isfile(f"{folderPath}/NOTES.md")


def test_zip_template_accepts_name_without_extension(dbConnWithProjectCategory):
    conn, templatesFolder = dbConnWithProjectCategory
    with zipfile.ZipFile(f"{templatesFolder}/custom.zip", "w") as zipHandle:
        zipHandle.writestr("NOTES.md", "hello")

    _code, _title, _folderPath, templateUsed = add_project(
        log=log, dbConn=conn, categoryRef="P11", templateName="custom", projectTitle="Another"
    ).get()
    assert templateUsed == "custom.zip"


def test_unknown_template_raises_clear_error(dbConnWithProjectCategory):
    conn, _ = dbConnWithProjectCategory
    with pytest.raises(ValueError):
        add_project(log=log, dbConn=conn, categoryRef="P11", templateName="does-not-exist", projectTitle="X").get()


def test_unknown_category_raises_clear_error(dbConnWithProjectCategory):
    conn, _ = dbConnWithProjectCategory
    with pytest.raises(ValueError):
        add_project(log=log, dbConn=conn, categoryRef="P99", templateName="blank", projectTitle="X").get()


def test_non_tty_with_no_template_defaults_to_blank(dbConnWithProjectCategory, monkeypatch):
    conn, _ = dbConnWithProjectCategory
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    _code, _title, folderPath, templateUsed = add_project(
        log=log, dbConn=conn, categoryRef="P11", templateName=None, projectTitle="Headless Project"
    ).get()
    assert templateUsed == "blank"
    assert os.path.isfile(f"{folderPath}/README.md")


def test_templates_are_scoped_to_their_own_category(dbConnWithProjectCategory):
    conn, templatesFolder = dbConnWithProjectCategory
    with zipfile.ZipFile(f"{templatesFolder}/custom.zip", "w") as zipHandle:
        zipHandle.writestr("NOTES.md", "hello")

    add_category(log=log, dbConn=conn, domain="projects", areaRef="P10", title="Marketing", description="").get()

    with pytest.raises(ValueError):
        add_project(log=log, dbConn=conn, categoryRef="P12", templateName="custom", projectTitle="X").get()


def test_category_without_templates_scaffolding_defaults_to_blank(dbConnWithProjectCategory, monkeypatch):
    conn, _ = dbConnWithProjectCategory
    conn.execute("DELETE FROM system_folders WHERE folder_key = ?", ("projects.11.04_templates",))
    conn.commit()
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)

    _code, _title, folderPath, templateUsed = add_project(
        log=log, dbConn=conn, categoryRef="P11", templateName=None, projectTitle="No Scaffold Project"
    ).get()
    assert templateUsed == "blank"
    assert os.path.isfile(f"{folderPath}/README.md")
