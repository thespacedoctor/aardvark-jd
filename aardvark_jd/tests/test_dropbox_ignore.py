import logging
import os
import subprocess
import sys

import pytest

from aardvark_jd import dropbox_ignore

log = logging.getLogger("test_dropbox_ignore")
log.addHandler(logging.NullHandler())

pytestmark = pytest.mark.skipif(
    sys.platform != "darwin", reason="com.dropbox.ignored is a macOS mechanism"
)


# ---------------------------------------------------------------- primitives

def test_set_ignored_then_is_ignored_round_trips(tmp_path):
    target = tmp_path / "00_INDEX"
    target.mkdir()
    assert dropbox_ignore.is_ignored(str(target)) is False

    dropbox_ignore.set_ignored(str(target))

    assert dropbox_ignore.is_ignored(str(target)) is True


def test_set_ignored_writes_the_attribute_dropbox_actually_reads(tmp_path):
    """*independent check of the on-disk name and value, via `/usr/bin/xattr`*"""
    target = tmp_path / "00_INDEX"
    target.mkdir()
    dropbox_ignore.set_ignored(str(target))

    written = subprocess.run(
        ["xattr", "-p", "com.dropbox.ignored", str(target)],
        capture_output=True, text=True, check=True,
    )
    assert written.stdout.strip() == "1"


def test_set_ignored_is_idempotent(tmp_path):
    target = tmp_path / "00_INDEX"
    target.mkdir()
    dropbox_ignore.set_ignored(str(target))
    dropbox_ignore.set_ignored(str(target))
    assert dropbox_ignore.is_ignored(str(target)) is True


def test_is_ignored_is_false_for_a_missing_path():
    assert dropbox_ignore.is_ignored("/no/such/path/anywhere") is False


def test_set_ignored_raises_oserror_on_a_missing_path():
    with pytest.raises(OSError):
        dropbox_ignore.set_ignored("/no/such/path/anywhere")


# ---------------------------------------------------------------- assert_index_ignored

@pytest.fixture
def systemRoot(tmp_path):
    """*a plausible aardvark root with a `00_INDEX🗂️` folder holding the db*"""
    root = tmp_path / "MySystem"
    indexDir = root / "00_INDEX🗂️"
    indexDir.mkdir(parents=True)
    (indexDir / "aardvark.db").write_bytes(b"")
    return root, indexDir


def test_assert_index_ignored_sets_the_attribute_when_inside_a_dropbox_tree(systemRoot, monkeypatch):
    root, indexDir = systemRoot
    monkeypatch.setattr(
        "aardvark_jd.dropbox_client.local_dropbox_roots", lambda: [str(root.parent)],
    )

    dropbox_ignore.assert_index_ignored(str(root), log)

    assert dropbox_ignore.is_ignored(str(indexDir)) is True


def test_assert_index_ignored_is_a_no_op_outside_any_dropbox_tree(systemRoot, monkeypatch):
    root, indexDir = systemRoot
    monkeypatch.setattr("aardvark_jd.dropbox_client.local_dropbox_roots", lambda: [])

    dropbox_ignore.assert_index_ignored(str(root), log)

    assert dropbox_ignore.is_ignored(str(indexDir)) is False


def test_assert_index_ignored_skips_the_syscall_when_already_ignored(systemRoot, monkeypatch):
    root, indexDir = systemRoot
    monkeypatch.setattr(
        "aardvark_jd.dropbox_client.local_dropbox_roots", lambda: [str(root.parent)],
    )
    dropbox_ignore.set_ignored(str(indexDir))

    calls = []
    monkeypatch.setattr(dropbox_ignore, "set_ignored", lambda path: calls.append(path))
    dropbox_ignore.assert_index_ignored(str(root), log)

    assert calls == []


def test_assert_index_ignored_warns_but_does_not_raise_on_non_macos(systemRoot, monkeypatch):
    root, indexDir = systemRoot
    monkeypatch.setattr(
        "aardvark_jd.dropbox_client.local_dropbox_roots", lambda: [str(root.parent)],
    )
    monkeypatch.setattr(dropbox_ignore, "is_supported", lambda: False)

    warnings = []
    monkeypatch.setattr(log, "warning", lambda msg, *args: warnings.append(msg % args if args else msg))
    dropbox_ignore.assert_index_ignored(str(root), log)

    assert any("only supported on macOS" in message for message in warnings)
    assert dropbox_ignore.is_ignored(str(indexDir)) is False


def test_assert_index_ignored_warns_but_does_not_raise_when_the_syscall_fails(systemRoot, monkeypatch, capsys):
    root, _indexDir = systemRoot
    monkeypatch.setattr(
        "aardvark_jd.dropbox_client.local_dropbox_roots", lambda: [str(root.parent)],
    )

    def boom(path):
        raise OSError(1, "Operation not permitted", path)

    monkeypatch.setattr(dropbox_ignore, "set_ignored", boom)

    # MUST NOT RAISE - THE COMMAND CARRIES ON.
    dropbox_ignore.assert_index_ignored(str(root), log)

    assert "could not exclude the aardvark index" in capsys.readouterr().err


def test_assert_index_ignored_swallows_a_dropbox_root_lookup_failure(systemRoot, monkeypatch):
    root, _indexDir = systemRoot

    def boom():
        raise OSError("dropbox info.json unreadable")

    monkeypatch.setattr("aardvark_jd.dropbox_client.local_dropbox_roots", boom)
    warnings = []
    monkeypatch.setattr(log, "warning", lambda msg, *args: warnings.append(msg % args if args else msg))

    dropbox_ignore.assert_index_ignored(str(root), log)  # MUST NOT RAISE

    assert any("inside a Dropbox tree" in message for message in warnings)


def test_assert_index_ignored_handles_a_missing_index_directory(tmp_path, monkeypatch):
    root = tmp_path / "Broken"
    root.mkdir()
    monkeypatch.setattr(
        "aardvark_jd.dropbox_client.local_dropbox_roots", lambda: [str(tmp_path)],
    )
    # NO `00_INDEX` FOLDER - MUST NOT RAISE.
    dropbox_ignore.assert_index_ignored(str(root), log)


def test_assert_index_ignored_swallows_a_non_filenotfound_oserror_from_find_db_path(systemRoot, monkeypatch):
    root, _indexDir = systemRoot
    monkeypatch.setattr(
        "aardvark_jd.dropbox_client.local_dropbox_roots", lambda: [str(root.parent)],
    )

    def denied(rootPath):
        raise PermissionError(13, "Permission denied", rootPath)

    monkeypatch.setattr("aardvark_jd.paths.find_db_path", denied)
    dropbox_ignore.assert_index_ignored(str(root), log)  # MUST NOT RAISE
