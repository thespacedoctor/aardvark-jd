import os

import pytest
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
    assert "A.10-19" in capsys.readouterr().out

    cl_utils.main(docopt(doc, ["add_category", "areas", "10", "Doctors", "desc"]))
    assert "A.11" in capsys.readouterr().out

    cl_utils.main(docopt(doc, ["add_id", "areas", "11", "Cardiologist", "desc"]))
    assert "A.11.01" in capsys.readouterr().out

    cl_utils.main(docopt(doc, ["search", "cardiologist"]))
    assert "A.11.01" in capsys.readouterr().out


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
    assert "A.10-19" in out
    assert "10-19 Health Y" in out

    # a freshly initialised system needs no repair
    cl_utils.main(docopt(doc, ["repair_emoji"]))
    assert "already carries its declared emoji" in capsys.readouterr().out

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
    assert "10-19 Taxes T" in capsys.readouterr().out
