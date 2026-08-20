from docopt import docopt

from aardvark_jd import cl_utils, commands, help_text


def test_full_help_is_the_docstring_unchanged():
    assert help_text.full_help(cl_utils.__doc__) == cl_utils.__doc__


def test_short_help_keeps_every_common_command():
    short = help_text.short_help(cl_utils.__doc__)
    for name in commands.names(commands.COMMON):
        assert f"aardvark {name}" in short, name


def test_short_help_hides_every_advanced_command():
    short = help_text.short_help(cl_utils.__doc__)
    for name in commands.names(commands.ADVANCED):
        assert f"aardvark {name}" not in short, name


def test_short_help_points_at_help_all():
    assert "--help-all" in help_text.short_help(cl_utils.__doc__)


def test_short_help_prunes_arguments_only_advanced_commands_use():
    short = help_text.short_help(cl_utils.__doc__)
    # `apiUrl` IS ONLY EVER USED BY connect_craft, WHICH IS ADVANCED
    assert "apiUrl" not in short
    # `category` IS USED BY add_id, WHICH IS COMMON, SO IT MUST SURVIVE
    assert "category" in short


def test_short_help_has_no_double_blank_lines():
    assert "\n\n\n" not in help_text.short_help(cl_utils.__doc__)


def test_hiding_commands_does_not_break_the_real_grammar():
    """the abridged screen is display-only - docopt still parses everything"""
    for name in commands.names(commands.ADVANCED):
        pass
    assert docopt(cl_utils.__doc__, ["craft_sync"])["craft_sync"] is True
    assert docopt(cl_utils.__doc__, ["gdrive_sync"])["gdrive_sync"] is True
