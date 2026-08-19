import os

import pytest
import yaml
from docopt import docopt

from aardvark_jd import cl_utils

doc = cl_utils.__doc__


@pytest.mark.parametrize("command,expectedKey", [
    ("init TestSystem /tmp/somewhere", "init"),
    ("new_project blank Title", "new_project"),
    ("add_area areas Health desc", "add_area"),
    ("add_category areas 10 Doctors desc", "add_category"),
    ("add_id areas 11 Cardiologist desc", "add_id"),
    ("set_emoji areas 10 X", "set_emoji"),
    ("repair_emoji", "repair_emoji"),
    ("search cardio", "search"),
    ("connect_craft https://connect.craft.do/links/abc/api/v1 my-token", "connect_craft"),
    ("craft_sync", "craft_sync"),
])
def test_docopt_parses_each_subcommand(command, expectedKey):
    args = docopt(doc, command.split(" "))
    assert args[expectedKey] is True


@pytest.mark.parametrize("command", [
    "add_area areas Health desc",
    "add_category areas 10 Doctors desc",
    "new_project blank Title",
])
def test_docopt_accepts_the_emoji_flag(command):
    assert docopt(doc, command.split(" ") + ["-e", "X"])["--emoji"] == "X"
    assert docopt(doc, command.split(" ") + ["--emoji", "X"])["--emoji"] == "X"


def test_emoji_flag_and_set_emoji_positional_do_not_collide():
    # `--emoji` is an option on the add_* commands while `<emoji>` is a
    # positional on set_emoji, so check docopt keeps the two apart
    args = docopt(doc, ["set_emoji", "areas", "10", "X"])
    assert args["<emoji>"] == "X"
    assert args["--emoji"] is None


@pytest.fixture
def isolatedHome(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    return tmp_path


def test_main_end_to_end(isolatedHome, monkeypatch, capsys):
    rootParent = str(isolatedHome / "root_parent")
    os.makedirs(rootParent)

    cl_utils.main(docopt(doc, ["init", "TestSystem", rootParent]))
    assert "initialised" in capsys.readouterr().out

    cl_utils.main(docopt(doc, ["add_area", "areas", "Health", "desc"]))
    assert "A10-19" in capsys.readouterr().out

    cl_utils.main(docopt(doc, ["add_category", "areas", "10", "Doctors", "desc"]))
    assert "A11" in capsys.readouterr().out

    cl_utils.main(docopt(doc, ["add_id", "areas", "11", "Cardiologist", "desc"]))
    assert "A11.10" in capsys.readouterr().out

    cl_utils.main(docopt(doc, ["search", "cardiologist"]))
    assert "A11.10" in capsys.readouterr().out


def test_main_reports_missing_system(isolatedHome, capsys):
    with pytest.raises(SystemExit) as excInfo:
        cl_utils.main(docopt(doc, ["search", "anything"]))
    assert excInfo.value.code == 1
    assert "run `aardvark init" in capsys.readouterr().err


def test_main_reports_clear_error_for_invalid_domain(isolatedHome, capsys):
    rootParent = str(isolatedHome / "root_parent")
    os.makedirs(rootParent)
    cl_utils.main(docopt(doc, ["init", "TestSystem", rootParent]))
    capsys.readouterr()

    with pytest.raises(SystemExit) as excInfo:
        cl_utils.main(docopt(doc, ["add_area", "projects", "X", "desc"]))
    assert excInfo.value.code == 1
    assert "error:" in capsys.readouterr().err


def test_main_set_emoji_and_repair_emoji_end_to_end(isolatedHome, monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    rootParent = str(isolatedHome / "root_parent")
    os.makedirs(rootParent)

    cl_utils.main(docopt(doc, ["init", "TestSystem", rootParent]))
    cl_utils.main(docopt(doc, ["add_area", "areas", "Health", "desc", "-e", "X"]))
    capsys.readouterr()

    cl_utils.main(docopt(doc, ["set_emoji", "areas", "10", "Y"]))
    out = capsys.readouterr().out
    assert "A10-19" in out
    assert "A10_19_healthY" in out

    # a freshly initialised system needs no repair
    cl_utils.main(docopt(doc, ["repair_emoji"]))
    assert "already matches the current naming convention" in capsys.readouterr().out

    cl_utils.main(docopt(doc, ["set_emoji", "system", "root.areas", "Z"]))
    capsys.readouterr()
    cl_utils.main(docopt(doc, ["repair_emoji"]))
    assert "root.areas" in capsys.readouterr().out


def test_main_emoji_flag_skips_the_suggester(isolatedHome, monkeypatch, capsys):
    from aardvark_jd import emoji_picker

    monkeypatch.setattr("sys.stdin.isatty", lambda: False)

    def boom(*args, **kwargs):
        raise AssertionError("--emoji must bypass the Claude API entirely")

    monkeypatch.setattr(emoji_picker, "_suggest_via_claude", boom)

    rootParent = str(isolatedHome / "root_parent")
    os.makedirs(rootParent)
    cl_utils.main(docopt(doc, ["init", "TestSystem", rootParent]))
    capsys.readouterr()

    cl_utils.main(docopt(doc, ["add_area", "areas", "Taxes", "desc", "-e", "T"]))
    assert "A10_19_taxesT" in capsys.readouterr().out


_CRAFT_API_URL = "https://connect.craft.do/links/abc123/api/v1"


class FakeCraftClient(object):
    """*records every folder/document/block created or updated, without any HTTP calls*"""

    def __init__(self, apiUrl, apiToken):
        self.apiUrl = apiUrl
        self.apiToken = apiToken
        self._counter = 0
        self.folders = []
        self.documents = []
        self.blocksAdded = []
        self.blocksUpdated = []

    def _next_id(self, prefix):
        self._counter += 1
        return f"{prefix}-{self._counter}"

    def list_folders(self):
        """*rebuild the nested tree the real `GET /folders` returns, from what's been created*"""

        def children_of(parentFolderId):
            return [
                {"id": folderId, "name": name, "folders": children_of(folderId)}
                for folderId, name, parent in self.folders if parent == parentFolderId
            ]

        return children_of(None)

    def folder_deep_link(self, folderId, title):
        return f"craftdocs://openfolder?folderId={folderId}&spaceId=space-1&title={title}"

    def create_folder(self, name, parentFolderId=None):
        folderId = self._next_id("folder")
        self.folders.append((folderId, name, parentFolderId))
        return folderId

    def create_document(self, title, folderId=None):
        documentId = self._next_id("doc")
        self.documents.append((documentId, title, folderId))
        return documentId, f"https://craft.example/doc/{documentId}"

    def add_block(self, documentId, markdown, position="end"):
        blockId = self._next_id("block")
        self.blocksAdded.append((documentId, markdown, blockId))
        return blockId

    def update_block(self, blockId, markdown):
        self.blocksUpdated.append((blockId, markdown))

    def index_bodies(self):
        """*every index block's markdown body, as added or later updated*"""
        return [markdown for _documentId, markdown, _blockId in self.blocksAdded] + \
            [markdown for _blockId, markdown in self.blocksUpdated]


@pytest.fixture
def fakeCraftClient(monkeypatch):
    client = FakeCraftClient(apiUrl=_CRAFT_API_URL, apiToken="fake-token")
    monkeypatch.setattr("aardvark_jd.craft_sync.CraftClient", lambda apiUrl, apiToken: client)
    return client


def test_connect_craft_persists_settings_and_runs_initial_sync(isolatedHome, fakeCraftClient, capsys):
    rootParent = str(isolatedHome / "root_parent")
    os.makedirs(rootParent)
    cl_utils.main(docopt(doc, ["init", "TestSystem", rootParent]))
    capsys.readouterr()

    settingsPath = str(isolatedHome / ".config" / "aardvark" / "aardvark.yaml")
    cl_utils.main(docopt(doc, ["connect_craft", _CRAFT_API_URL, "my-token", "-s", settingsPath]))
    out = capsys.readouterr().out
    assert "craft connected" in out
    assert len(fakeCraftClient.folders) >= 5

    with open(settingsPath) as stream:
        savedSettings = yaml.safe_load(stream)
    assert savedSettings["craft"]["enabled"] is True
    assert savedSettings["craft"]["api_url"] == _CRAFT_API_URL
    assert savedSettings["craft"]["api_token"] == "my-token"


def test_connect_craft_without_s_flag_still_persists_to_the_default_settings_file(
    isolatedHome, fakeCraftClient, capsys,
):
    """*regression test for the bug where craft.enabled never survived past the connecting process*

    `connect_craft` used to only write settings back out when `-s` was
    passed explicitly, unlike `init` which already falls back to the
    default `~/.config/aardvark/aardvark.yaml`. That meant a bare
    `connect_craft <url> <token>` (no `-s`) looked like it worked - the
    initial sync ran - but `craft.enabled` was never saved, so every
    later command silently skipped its auto-push.
    """
    rootParent = str(isolatedHome / "root_parent")
    os.makedirs(rootParent)
    cl_utils.main(docopt(doc, ["init", "TestSystem", rootParent]))
    capsys.readouterr()

    cl_utils.main(docopt(doc, ["connect_craft", _CRAFT_API_URL, "my-token"]))
    assert "craft connected" in capsys.readouterr().out

    defaultSettingsPath = str(isolatedHome / ".config" / "aardvark" / "aardvark.yaml")
    with open(defaultSettingsPath) as stream:
        savedSettings = yaml.safe_load(stream)
    assert savedSettings["craft"]["enabled"] is True

    # THE REAL REGRESSION TEST: A LATER COMMAND, ALSO RUN WITHOUT `-s`, MUST
    # PICK UP `craft.enabled` FROM THAT SAME DEFAULT FILE AND AUTO-PUSH.
    fakeCraftClient.folders.clear()
    cl_utils.main(docopt(doc, ["add_area", "areas", "Health", "desc"]))
    capsys.readouterr()
    assert any(name.startswith("A10-19 health") for _id, name, _parent in fakeCraftClient.folders)


def test_craft_sync_command_requires_connect_first(isolatedHome, capsys):
    rootParent = str(isolatedHome / "root_parent")
    os.makedirs(rootParent)
    cl_utils.main(docopt(doc, ["init", "TestSystem", rootParent]))
    capsys.readouterr()

    with pytest.raises(SystemExit) as excInfo:
        cl_utils.main(docopt(doc, ["craft_sync"]))
    assert excInfo.value.code == 1
    assert "craft is not connected" in capsys.readouterr().err


def test_add_area_auto_pushes_to_craft_once_connected(isolatedHome, fakeCraftClient, capsys):
    rootParent = str(isolatedHome / "root_parent")
    os.makedirs(rootParent)
    cl_utils.main(docopt(doc, ["init", "TestSystem", rootParent]))
    capsys.readouterr()

    settingsPath = str(isolatedHome / ".config" / "aardvark" / "aardvark.yaml")
    cl_utils.main(docopt(doc, ["connect_craft", _CRAFT_API_URL, "my-token", "-s", settingsPath]))
    capsys.readouterr()

    cl_utils.main(docopt(doc, ["add_area", "areas", "Health", "desc"]))
    assert "A10-19" in capsys.readouterr().out

    # the craft folder mirrors the on-disk name (lowercased, emoji suffixed)
    folderTitles = {name for _id, name, _parent in fakeCraftClient.folders}
    assert any(name.startswith("A10-19 health") for name in folderTitles)

    # THE DOMAIN-ROOT INDEX MUST ACTUALLY LIST THE NEW AREA, NOT JUST HAVE ITS
    # FOLDER CREATED - THE PRIOR VERSION OF THIS TEST ONLY CHECKED THE LATTER,
    # WHICH IS HOW A BLANK INDEX DOCUMENT SHIPPED UNDETECTED.
    assert any("A10-19 health" in body for body in fakeCraftClient.index_bodies())


def test_repair_emoji_auto_pushes_to_craft_once_connected(isolatedHome, monkeypatch, fakeCraftClient, capsys):
    """*regression test: `repair_emoji` used to never sync to craft at all, even when connected*"""
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    rootParent = str(isolatedHome / "root_parent")
    os.makedirs(rootParent)
    cl_utils.main(docopt(doc, ["init", "TestSystem", rootParent]))
    cl_utils.main(docopt(doc, ["add_area", "areas", "Health", "desc", "-e", "X"]))
    capsys.readouterr()

    settingsPath = str(isolatedHome / ".config" / "aardvark" / "aardvark.yaml")
    cl_utils.main(docopt(doc, ["connect_craft", _CRAFT_API_URL, "my-token", "-s", settingsPath]))
    capsys.readouterr()

    cl_utils.main(docopt(doc, ["set_emoji", "areas", "10", "Y"]))
    capsys.readouterr()

    blocksUpdatedBefore = len(fakeCraftClient.blocksUpdated)
    cl_utils.main(docopt(doc, ["repair_emoji"]))
    capsys.readouterr()
    assert len(fakeCraftClient.blocksUpdated) > blocksUpdatedBefore
    assert any("A10-19 healthY" in body for body in fakeCraftClient.index_bodies())
