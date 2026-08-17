import os

import pytest
from docopt import docopt

from aardvark import cl_utils

doc = cl_utils.__doc__


@pytest.mark.parametrize("command,expectedKey", [
    ("init TestSystem /tmp/somewhere", "init"),
    ("new_project blank Title", "new_project"),
    ("add_area areas Health desc", "add_area"),
    ("add_category areas 10 Doctors desc", "add_category"),
    ("add_id areas 11 Cardiologist desc", "add_id"),
    ("search cardio", "search"),
])
def test_docopt_parses_each_subcommand(command, expectedKey):
    args = docopt(doc, command.split(" "))
    assert args[expectedKey] is True


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
