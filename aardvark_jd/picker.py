#!/usr/bin/env python
# encoding: utf-8
"""
*A dependency-free arrow-key single-select prompt, for drilling down through the index*

Written against `termios`/`tty` directly rather than pulling in curses or a
third-party prompt library: aardvark's only runtime dependencies are
`pyyaml`, `fundamentals`, `docopt`, `emoji`, `anthropic` and `requests`,
and a one-screen chooser does not justify adding to that list.

The menu is drawn to **stderr**, not stdout, so a caller's real output
stays pipeable while the chooser is on screen. The terminal is always
restored through a `finally`, including on `KeyboardInterrupt`, so a
cancelled prompt can never leave the user's shell in raw mode.

Author
: David Young
"""

import os
import select
import sys

_ESC = "\x1b"
_UP = "up"
_DOWN = "down"
_LEFT = "left"
_RIGHT = "right"
_ENTER = "enter"
_CANCEL = "cancel"

# HOW LONG TO WAIT FOR THE REST OF A CSI SEQUENCE BEFORE DECIDING A BARE
# `ESC` REALLY WAS A BARE `ESC` (THE USER PRESSING ESCAPE TO CANCEL).
_ESCAPE_TIMEOUT_SECONDS = 0.05


class NotATtyError(Exception):
    """*raised when `select` is called without an interactive terminal to draw on*"""
    pass


def select_one(options, title="", readKey=None, stream=None, initialIndex=0):
    """
    *let the user choose one of `options` with the arrow keys*

    **Key Arguments:**

    - ``options`` -- an ordered list of `(value, label)` pairs
    - ``title`` -- a heading drawn above the list. Default *""*.
    - ``readKey`` -- an injectable key reader returning one of the module's key constants, for testing. Default *None*, meaning read the real terminal.
    - ``stream`` -- where to draw. Default *None*, meaning `sys.stderr`.
    - ``initialIndex`` -- which option starts highlighted, so a caller can pre-select the most likely answer. Default *0*.

    **Return:**

    - ``value`` -- the chosen option's value, or `None` if the user cancelled

    **Raises:**

    - ``NotATtyError`` -- if there is no interactive terminal and no `readKey` was injected

    **Usage:**

    ```python
    from aardvark_jd.picker import select_one
    chosen = select_one([("a", "Areas"), ("r", "Resources")], title="Pick a domain")
    ```
    """
    if not options:
        return None

    stream = stream or sys.stderr
    if readKey is None:
        if not (sys.stdin.isatty() and stream.isatty()):
            raise NotATtyError("an interactive terminal is required")
        readKey = _raw_key_reader()

    selectedIndex = initialIndex if 0 <= initialIndex < len(options) else 0
    drawnLines = 0
    try:
        while True:
            drawnLines = _render(options, selectedIndex, title, stream, drawnLines)
            key = readKey()
            if key == _UP:
                selectedIndex = (selectedIndex - 1) % len(options)
            elif key == _DOWN:
                selectedIndex = (selectedIndex + 1) % len(options)
            elif key in (_ENTER, _RIGHT):
                return options[selectedIndex][0]
            elif key in (_CANCEL, _LEFT):
                return None
    finally:
        _clear(stream, drawnLines)


def _render(options, selectedIndex, title, stream, previouslyDrawn):
    """
    *(re)draw the menu in place, returning how many lines it occupies*

    **Key Arguments:**

    - ``options`` -- the `(value, label)` pairs
    - ``selectedIndex`` -- the index currently highlighted
    - ``title`` -- the heading, or `""` for none
    - ``stream`` -- the stream to draw on
    - ``previouslyDrawn`` -- how many lines the previous draw occupied

    **Return:**

    - ``drawnLines`` -- how many lines this draw occupies
    """
    if previouslyDrawn:
        stream.write(f"{_ESC}[{previouslyDrawn}A")

    lines = []
    if title:
        lines.append(f"{_ESC}[1m{title}{_ESC}[0m")
    for index, (_value, label) in enumerate(options):
        if index == selectedIndex:
            lines.append(f"{_ESC}[7m> {label}{_ESC}[0m")
        else:
            lines.append(f"  {label}")

    for line in lines:
        stream.write(f"{_ESC}[2K{line}\n")
    stream.flush()
    return len(lines)


def _clear(stream, drawnLines):
    """
    *erase the menu, leaving the cursor where it started*

    **Key Arguments:**

    - ``stream`` -- the stream the menu was drawn on
    - ``drawnLines`` -- how many lines the menu occupies
    """
    if not drawnLines:
        return
    stream.write(f"{_ESC}[{drawnLines}A")
    for _ in range(drawnLines):
        stream.write(f"{_ESC}[2K\n")
    stream.write(f"{_ESC}[{drawnLines}A")
    stream.flush()


def _raw_key_reader():
    """
    *build a key reader that puts the terminal into raw mode for each keypress*

    Raw mode is entered and left around every single read rather than held
    for the whole menu, so an exception anywhere in the caller can never
    strand the terminal - `tcsetattr` in the `finally` always runs.

    **Return:**

    - ``readKey`` -- a callable returning one of the module's key constants
    """
    import termios
    import tty

    def readKey():
        fd = sys.stdin.fileno()
        savedAttributes = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            firstByte = os.read(fd, 1).decode("utf-8", "ignore")
            if firstByte in ("\r", "\n"):
                return _ENTER
            if firstByte in ("q", "\x03"):
                return _CANCEL
            if firstByte != _ESC:
                return firstByte
            # A CSI SEQUENCE ARRIVES ALL AT ONCE; A LONE `ESC` DOES NOT. WAIT
            # BRIEFLY TO TELL AN ARROW KEY APART FROM THE ESCAPE KEY ITSELF.
            readable, _writable, _errored = select.select([fd], [], [], _ESCAPE_TIMEOUT_SECONDS)
            if not readable:
                return _CANCEL
            rest = os.read(fd, 2).decode("utf-8", "ignore")
            return {
                "[A": _UP, "[B": _DOWN, "[C": _RIGHT, "[D": _LEFT,
                "OA": _UP, "OB": _DOWN, "OC": _RIGHT, "OD": _LEFT,
            }.get(rest, _CANCEL)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, savedAttributes)

    return readKey
