import io

import pytest

from aardvark_jd import picker


def _keys(*sequence):
    """*a readKey stub returning each key in turn*"""
    remaining = list(sequence)
    return lambda: remaining.pop(0)


def _stream():
    return io.StringIO()


OPTIONS = [("a", "Areas"), ("r", "Resources"), ("p", "Projects")]


def test_enter_selects_the_first_option_by_default():
    chosen = picker.select_one(OPTIONS, readKey=_keys("enter"), stream=_stream())
    assert chosen == "a"


def test_down_then_enter_selects_the_second():
    chosen = picker.select_one(OPTIONS, readKey=_keys("down", "enter"), stream=_stream())
    assert chosen == "r"


def test_up_wraps_around_to_the_last_option():
    chosen = picker.select_one(OPTIONS, readKey=_keys("up", "enter"), stream=_stream())
    assert chosen == "p"


def test_down_wraps_around_to_the_first_option():
    chosen = picker.select_one(
        OPTIONS, readKey=_keys("down", "down", "down", "enter"), stream=_stream()
    )
    assert chosen == "a"


def test_cancel_returns_none():
    assert picker.select_one(OPTIONS, readKey=_keys("cancel"), stream=_stream()) is None


def test_left_also_cancels_so_it_can_mean_go_back():
    assert picker.select_one(OPTIONS, readKey=_keys("left"), stream=_stream()) is None


def test_right_selects_so_it_can_mean_descend():
    assert picker.select_one(OPTIONS, readKey=_keys("right"), stream=_stream()) == "a"


def test_an_empty_option_list_returns_none_without_reading_a_key():
    assert picker.select_one([], readKey=_keys(), stream=_stream()) is None


def test_the_title_and_every_label_are_drawn():
    stream = _stream()
    picker.select_one(OPTIONS, title="Pick one", readKey=_keys("enter"), stream=stream)
    drawn = stream.getvalue()
    assert "Pick one" in drawn
    for _value, label in OPTIONS:
        assert label in drawn


def test_the_menu_is_erased_on_the_way_out():
    stream = _stream()
    picker.select_one(OPTIONS, readKey=_keys("enter"), stream=stream)
    # THE ERASE PASS WRITES A CLEAR-LINE FOR EVERY LINE IT DREW
    assert "\x1b[2K" in stream.getvalue()


def test_no_tty_and_no_injected_reader_raises(monkeypatch):
    class NotATty(io.StringIO):
        def isatty(self):
            return False

    monkeypatch.setattr("sys.stdin", NotATty())
    with pytest.raises(picker.NotATtyError):
        picker.select_one(OPTIONS, stream=NotATty())
