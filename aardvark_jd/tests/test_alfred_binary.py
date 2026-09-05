import os
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from aardvark_jd.alfred.binary import (
    binary_resolution,
    console_script_path,
    read_pointer,
    remove_pointer,
    resolve,
    write_pointer,
)


def test_derives_console_script_path_from_python_executable():
    # ARRANGE
    executable = "/some/venv/bin/python3"

    # ACT
    result = console_script_path(executable)

    # ASSERT
    assert result == Path("/some/venv/bin/aardvark")


def test_writes_binary_path_with_trailing_newline_and_creates_parent_directory(
    tmp_path,
):
    # ARRANGE
    binary_path = tmp_path / "venv" / "bin" / "aardvark"
    pointer_path = tmp_path / "missing" / "alfred-binary-path"

    # ACT
    result = write_pointer(binary_path, pointer_path)

    # ASSERT
    assert result == pointer_path
    assert pointer_path.read_text() == f"{binary_path}\n"


def test_expands_default_pointer_path_at_call_time(tmp_path, monkeypatch):
    # ARRANGE
    first_home = tmp_path / "first-home"
    second_home = tmp_path / "second-home"
    first_binary_path = tmp_path / "first" / "aardvark"
    second_binary_path = tmp_path / "second" / "aardvark"
    first_pointer_path = first_home / ".config" / "aardvark" / "alfred-binary-path"
    second_pointer_path = second_home / ".config" / "aardvark" / "alfred-binary-path"

    # ACT
    monkeypatch.setenv("HOME", str(first_home))
    first_result = write_pointer(first_binary_path)
    monkeypatch.setenv("HOME", str(second_home))
    second_result = write_pointer(second_binary_path)

    # ASSERT
    assert first_result == first_pointer_path
    assert second_result == second_pointer_path
    assert first_pointer_path.read_text() == f"{first_binary_path}\n"
    assert second_pointer_path.read_text() == f"{second_binary_path}\n"


def test_reads_stripped_binary_path_from_default_pointer_file(tmp_path, monkeypatch):
    # ARRANGE
    monkeypatch.setenv("HOME", str(tmp_path))
    pointer_path = tmp_path / ".config" / "aardvark" / "alfred-binary-path"
    pointer_path.parent.mkdir(parents=True)
    pointer_path.write_text("  /some/venv/bin/aardvark  \n", encoding="utf-8")

    # ACT
    result = read_pointer()

    # ASSERT
    assert result == "/some/venv/bin/aardvark"


def test_returns_none_when_pointer_file_does_not_exist(tmp_path):
    # ARRANGE
    pointer_path = tmp_path / "alfred-binary-path"

    # ACT
    result = read_pointer(pointer_path)

    # ASSERT
    assert result is None


def test_returns_none_when_pointer_file_contains_only_whitespace(tmp_path):
    # ARRANGE
    pointer_path = tmp_path / "alfred-binary-path"
    pointer_path.write_text(" \n\t", encoding="utf-8")

    # ACT
    result = read_pointer(pointer_path)

    # ASSERT
    assert result is None


def test_removes_existing_pointer_file_and_returns_true(tmp_path):
    # ARRANGE
    pointer_path = tmp_path / "alfred-binary-path"
    pointer_path.write_text("/some/venv/bin/aardvark\n", encoding="utf-8")

    # ACT
    result = remove_pointer(pointer_path)

    # ASSERT
    assert result is True
    assert not pointer_path.exists()


def test_remove_pointer_is_idempotent_when_file_is_missing(tmp_path):
    # ARRANGE
    pointer_path = tmp_path / "alfred-binary-path"

    # ACT
    results = [remove_pointer(pointer_path), remove_pointer(pointer_path)]

    # ASSERT
    assert results == [False, False]


def test_resolve_returns_missing_when_config_and_pointer_are_unset(tmp_path):
    # ARRANGE
    pointer_path = tmp_path / "alfred-binary-path"

    # ACT
    result = resolve(pointerPath=pointer_path)

    # ASSERT
    assert result.state == "missing"
    assert result.path is None
    assert result.source is None


def test_resolve_returns_ok_for_executable_config_override(tmp_path, monkeypatch):
    # ARRANGE
    config_path = "/configured/venv/bin/aardvark"
    pointer_path = tmp_path / "alfred-binary-path"
    pointer_path.mkdir()
    monkeypatch.setattr(
        os,
        "access",
        lambda path, mode: path == config_path and mode == os.X_OK,
    )

    # ACT
    result = resolve(configVariable=config_path, pointerPath=pointer_path)

    # ASSERT
    assert result.state == "ok"
    assert result.path == config_path
    assert result.source == "config"


def test_resolve_returns_dead_for_non_executable_config_without_pointer_fallback(
    tmp_path,
    monkeypatch,
):
    # ARRANGE
    config_path = "/dead/configured/aardvark"
    pointer_candidate = "/working/pointer/aardvark"
    pointer_path = tmp_path / "alfred-binary-path"
    pointer_path.write_text(f"{pointer_candidate}\n", encoding="utf-8")
    monkeypatch.setattr(
        os,
        "access",
        lambda path, mode: path == pointer_candidate and mode == os.X_OK,
    )

    # ACT
    result = resolve(configVariable=config_path, pointerPath=pointer_path)

    # ASSERT
    assert result.state == "dead"
    assert result.path == config_path
    assert result.source == "config"


def test_resolve_blank_config_falls_through_to_executable_pointer(
    tmp_path,
    monkeypatch,
):
    # ARRANGE
    pointer_candidate = "/pointer/venv/bin/aardvark"
    pointer_path = tmp_path / "alfred-binary-path"
    pointer_path.write_text(f"{pointer_candidate}\n", encoding="utf-8")
    monkeypatch.setattr(
        os,
        "access",
        lambda path, mode: path == pointer_candidate and mode == os.X_OK,
    )

    # ACT
    result = resolve(configVariable=" \t", pointerPath=pointer_path)

    # ASSERT
    assert result.state == "ok"
    assert result.path == pointer_candidate
    assert result.source == "pointer"


def test_resolve_returns_ok_for_executable_pointer_when_config_is_unset(
    tmp_path,
    monkeypatch,
):
    # ARRANGE
    pointer_candidate = "/pointer/venv/bin/aardvark"
    pointer_path = tmp_path / "alfred-binary-path"
    pointer_path.write_text(f"{pointer_candidate}\n", encoding="utf-8")
    monkeypatch.setattr(
        os,
        "access",
        lambda path, mode: path == pointer_candidate and mode == os.X_OK,
    )

    # ACT
    result = resolve(pointerPath=pointer_path)

    # ASSERT
    assert result.state == "ok"
    assert result.path == pointer_candidate
    assert result.source == "pointer"


def test_resolve_returns_missing_when_pointer_is_blank(tmp_path):
    # ARRANGE
    pointer_path = tmp_path / "alfred-binary-path"
    pointer_path.write_text(" \n", encoding="utf-8")

    # ACT
    result = resolve(pointerPath=pointer_path)

    # ASSERT
    assert result.state == "missing"
    assert result.path is None
    assert result.source is None


def test_resolve_returns_dead_for_non_executable_pointer(tmp_path, monkeypatch):
    # ARRANGE
    pointer_candidate = "/dead/pointer/aardvark"
    pointer_path = tmp_path / "alfred-binary-path"
    pointer_path.write_text(f"{pointer_candidate}\n", encoding="utf-8")
    monkeypatch.setattr(os, "access", lambda path, mode: False)

    # ACT
    result = resolve(pointerPath=pointer_path)

    # ASSERT
    assert result.state == "dead"
    assert result.path == pointer_candidate
    assert result.source == "pointer"


def test_binary_resolution_is_immutable():
    # ARRANGE
    result = binary_resolution(
        state="ok",
        path="/some/venv/bin/aardvark",
        source="config",
    )

    # ACT AND ASSERT
    with pytest.raises(FrozenInstanceError):
        result.path = "/different/venv/bin/aardvark"
