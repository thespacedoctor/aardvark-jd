import re

import pytest

from aardvark_jd import cl_utils, commands

_USAGE_LINE_RE = re.compile(r"^\s+aardvark (\S+)", re.M)


def test_command_table_matches_docopt_usage():
    """the table and the docopt grammar must never drift apart"""
    usageCommands = set(_USAGE_LINE_RE.findall(cl_utils.__doc__))
    assert usageCommands == set(commands.names())


def test_every_command_is_grouped_and_summarised():
    for name, group, summary, completers in commands.COMMANDS:
        assert group in (commands.COMMON, commands.ADVANCED)
        assert summary and summary[0].islower()
        assert isinstance(completers, tuple)


def test_names_filters_by_group():
    common = commands.names(commands.COMMON)
    advanced = commands.names(commands.ADVANCED)
    assert set(common) & set(advanced) == set()
    assert set(common) | set(advanced) == set(commands.names())
    assert "add_id" in common
    assert "connect_gdrive" in advanced


def test_spec_and_summary_round_trip():
    name, group, summary, completers = commands.spec("add_category")
    assert name == "add_category"
    assert completers[0] == "area"
    assert commands.summary("add_category") == summary


def test_spec_returns_none_for_an_unknown_command():
    assert commands.spec("no_such_command") is None
    assert commands.summary("no_such_command") is None


@pytest.mark.parametrize("flag", ["-s", "--settings", "-e", "--emoji", "-t", "--template"])
def test_value_taking_flags_are_declared(flag):
    assert flag in commands.FLAGS_TAKING_A_VALUE
