import logging
import os

import pytest
import yaml

from aardvark_jd import db, emoji_picker, paths
from aardvark_jd.add_area import add_area
from aardvark_jd.add_category import add_category
from aardvark_jd.initialiser import initialiser

log = logging.getLogger("test_resolve_emoji")
log.addHandler(logging.NullHandler())


@pytest.fixture
def settingsFile(tmp_path):
    settingsPath = str(tmp_path / "settings.yaml")
    with open(settingsPath, "w") as stream:
        yaml.safe_dump({"version": 1, "system": {"name": None, "root_path": None}}, stream)
    return settingsPath


@pytest.fixture
def systemDbConn(tmp_path, settingsFile):
    rootPath = initialiser(
        log=log, systemName="My Life", parentPath=str(tmp_path), pathToSettingsFile=settingsFile
    ).get()
    dbConn = db.get_connection(paths.find_db_path(rootPath))
    yield dbConn
    dbConn.close()


@pytest.fixture
def noSuggester(monkeypatch):
    """*make any call to the Claude suggester an immediate test failure*"""

    def boom(*args, **kwargs):
        raise AssertionError("the Claude API must not be called on this path")

    monkeypatch.setattr(emoji_picker, "_suggest_via_claude", boom)


@pytest.fixture
def nonInteractive(monkeypatch):
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)


@pytest.fixture
def interactive(monkeypatch):
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)


# --------------------------------------------------------- chosen emoji wins


def test_chosen_emoji_skips_the_api_and_the_prompt(noSuggester, interactive, monkeypatch):
    def noInput(*args, **kwargs):
        raise AssertionError("must not prompt when an emoji was supplied")

    monkeypatch.setattr("builtins.input", noInput)
    assert emoji_picker.resolve_emoji("Doctors", "GP", chosenEmoji="🩺") == "🩺"


def test_chosen_emoji_is_stripped():
    assert emoji_picker.resolve_emoji("Doctors", chosenEmoji="  🩺  ") == "🩺"


@pytest.mark.parametrize("bad", ["a/b", "a\\b", "x\ny", ""])
def test_path_breaking_chosen_emoji_is_rejected(bad):
    if bad == "":
        with pytest.raises(ValueError, match="an emoji is required"):
            emoji_picker.validate_chosen_emoji(bad)
    else:
        with pytest.raises(ValueError, match="cannot be used in a folder name"):
            emoji_picker.validate_chosen_emoji(bad)


# ---------------------------------------------------------------- non-TTY


def test_non_tty_accepts_the_suggestion_without_prompting(nonInteractive, monkeypatch):
    monkeypatch.setattr(emoji_picker, "suggest_emoji", lambda *a, **k: "🩺")

    def noInput(*args, **kwargs):
        raise AssertionError("must not prompt in a non-interactive session")

    monkeypatch.setattr("builtins.input", noInput)
    assert emoji_picker.resolve_emoji("Doctors") == "🩺"


def test_non_tty_falls_back_offline_with_no_credentials(nonInteractive):
    # no anthropic credentials are configured in the test environment, so this
    # exercises the real degrade-to-offline path end to end
    assert emoji_picker.resolve_emoji("Hospital") == "🏥"


# -------------------------------------------------------------------- TTY


def test_tty_accepts_the_suggestion_on_a_bare_enter(interactive, monkeypatch, capsys):
    monkeypatch.setattr(emoji_picker, "suggest_emoji", lambda *a, **k: "🩺")
    monkeypatch.setattr("builtins.input", lambda *a, **k: "")

    assert emoji_picker.resolve_emoji("Doctors") == "🩺"
    assert "🩺" in capsys.readouterr().out


def test_tty_lets_the_user_replace_the_suggestion(interactive, monkeypatch):
    monkeypatch.setattr(emoji_picker, "suggest_emoji", lambda *a, **k: "🩺")
    monkeypatch.setattr("builtins.input", lambda *a, **k: "🏥")
    assert emoji_picker.resolve_emoji("Doctors") == "🏥"


def test_tty_reprompts_after_an_unusable_replacement(interactive, monkeypatch, capsys):
    monkeypatch.setattr(emoji_picker, "suggest_emoji", lambda *a, **k: "🩺")
    replies = iter(["a/b", "🏥"])
    monkeypatch.setattr("builtins.input", lambda *a, **k: next(replies))

    assert emoji_picker.resolve_emoji("Doctors") == "🏥"
    assert "cannot be used in a folder name" in capsys.readouterr().out


# -------------------------------------------------- wired through the workers


def test_add_area_honours_the_chosen_emoji(systemDbConn, noSuggester, interactive):
    _code, folderPath = add_area(
        log=log, dbConn=systemDbConn, domain="areas", title="Health",
        description="...", chosenEmoji="🩺",
    ).get()

    assert os.path.basename(folderPath) == "10-19 Health🩺"
    assert db.get_area(systemDbConn, "areas", 10)["emoji"] == "🩺"


def test_add_category_honours_the_chosen_emoji(systemDbConn, noSuggester, interactive):
    add_area(log=log, dbConn=systemDbConn, domain="areas", title="Health",
             description="...", chosenEmoji="🩺").get()
    _code, folderPath = add_category(
        log=log, dbConn=systemDbConn, domain="areas", areaRef="10", title="Doctors",
        description="...", chosenEmoji="👩‍⚕️",
    ).get()

    assert os.path.basename(folderPath) == "11 Doctors👩‍⚕️"
    assert db.get_category(systemDbConn, "areas", 11)["emoji"] == "👩‍⚕️"


def test_workers_respect_the_use_llm_setting(systemDbConn, noSuggester, nonInteractive):
    # noSuggester would raise if the API were consulted, so reaching a folder
    # name at all proves the setting was honoured
    _code, folderPath = add_area(
        log=log, dbConn=systemDbConn, domain="areas", title="Hospital",
        description="...", settings={"emoji": {"use_llm": False}},
    ).get()
    assert os.path.basename(folderPath) == "10-19 Hospital🏥"
