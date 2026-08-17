import logging
import os
import zipfile

import pytest
import yaml

from aardvark_jd import db, paths
from aardvark_jd.initialiser import initialiser
from aardvark_jd.new_project import new_project

log = logging.getLogger("test_new_project")
log.addHandler(logging.NullHandler())


@pytest.fixture
def dbConnAndTemplatesFolder(tmp_path):
    settingsPath = str(tmp_path / "settings.yaml")
    with open(settingsPath, "w") as stream:
        yaml.safe_dump({"version": 1, "system": {"name": None, "root_path": None}}, stream)
    rootPath = initialiser(
        log=log, systemName="Test", parentPath=str(tmp_path), pathToSettingsFile=settingsPath
    ).get()
    conn = db.get_connection(paths.find_db_path(rootPath))
    templatesFolder = paths.resolve(conn, "projects.system.04_templates")
    yield conn, templatesFolder
    conn.close()


def test_blank_scaffold(dbConnAndTemplatesFolder):
    conn, _ = dbConnAndTemplatesFolder
    title, folderPath, templateUsed = new_project(
        log=log, dbConn=conn, templateName="blank", projectTitle="My Project"
    ).get()

    assert title == "My Project"
    assert templateUsed == "blank"
    assert os.path.isfile(f"{folderPath}/README.md")
    assert os.path.isdir(f"{folderPath}/input")
    assert os.path.isdir(f"{folderPath}/output")

    row = conn.execute("SELECT * FROM projects WHERE title = ?", ("My Project",)).fetchone()
    assert row["template_used"] == "blank"


def test_zip_template_extraction(dbConnAndTemplatesFolder, tmp_path):
    conn, templatesFolder = dbConnAndTemplatesFolder

    customZipPath = f"{templatesFolder}/custom.zip"
    with zipfile.ZipFile(customZipPath, "w") as zipHandle:
        zipHandle.writestr("NOTES.md", "hello")

    title, folderPath, templateUsed = new_project(
        log=log, dbConn=conn, templateName="custom", projectTitle="Custom Project"
    ).get()

    assert templateUsed == "custom.zip"
    assert os.path.isfile(f"{folderPath}/NOTES.md")


def test_zip_template_accepts_name_without_extension(dbConnAndTemplatesFolder):
    conn, templatesFolder = dbConnAndTemplatesFolder
    with zipfile.ZipFile(f"{templatesFolder}/custom.zip", "w") as zipHandle:
        zipHandle.writestr("NOTES.md", "hello")

    _, _, templateUsed = new_project(
        log=log, dbConn=conn, templateName="custom", projectTitle="Another"
    ).get()
    assert templateUsed == "custom.zip"


def test_unknown_template_raises_clear_error(dbConnAndTemplatesFolder):
    conn, _ = dbConnAndTemplatesFolder
    with pytest.raises(ValueError):
        new_project(log=log, dbConn=conn, templateName="does-not-exist", projectTitle="X").get()


def test_non_interactive_without_title_raises(dbConnAndTemplatesFolder, monkeypatch):
    conn, _ = dbConnAndTemplatesFolder
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    with pytest.raises(ValueError):
        new_project(log=log, dbConn=conn, templateName="blank", projectTitle=None).get()


def test_non_tty_with_no_template_defaults_to_blank(dbConnAndTemplatesFolder, monkeypatch):
    conn, _ = dbConnAndTemplatesFolder
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    title, folderPath, templateUsed = new_project(
        log=log, dbConn=conn, templateName=None, projectTitle="Headless Project"
    ).get()
    assert templateUsed == "blank"
    assert os.path.isfile(f"{folderPath}/README.md")
