import logging
import os

from aardvark_jd import vocabulary

log = logging.getLogger("test_vocabulary")
log.addHandler(logging.NullHandler())


def test_an_unused_system_has_an_empty_vocabulary_and_no_file(tmp_path):
    """*never written by `init` - an unused system carries no empty file*"""
    assert vocabulary.load(str(tmp_path)) == frozenset()
    assert not os.path.exists(vocabulary.vocabulary_path(str(tmp_path)))


def test_remember_then_load_round_trips(tmp_path):
    vocabulary.remember(str(tmp_path), "pydantic", log=log)

    assert "pydantic" in vocabulary.load(str(tmp_path))


def test_the_file_is_created_lazily_on_the_first_dismissal(tmp_path):
    assert not os.path.exists(vocabulary.vocabulary_path(str(tmp_path)))
    vocabulary.remember(str(tmp_path), "postgres", log=log)
    assert os.path.exists(vocabulary.vocabulary_path(str(tmp_path)))


def test_words_are_stored_lowercase_sorted_and_deduplicated(tmp_path):
    """*stable on-disk order keeps Dropbox diffs and conflict copies minimal*"""
    for word in ("Zephyr", "pydantic", "ZEPHYR", "aardvark"):
        vocabulary.remember(str(tmp_path), word, log=log)

    with open(vocabulary.vocabulary_path(str(tmp_path))) as stream:
        stored = [line.strip() for line in stream if line.strip() and not line.startswith("#")]

    assert stored == ["aardvark", "pydantic", "zephyr"]


def test_the_file_carries_a_header_for_hand_editors(tmp_path):
    vocabulary.remember(str(tmp_path), "pydantic", log=log)

    with open(vocabulary.vocabulary_path(str(tmp_path))) as stream:
        firstLine = stream.readline()

    assert firstLine.startswith("#")


def test_comments_and_blank_lines_are_ignored_on_read(tmp_path):
    with open(vocabulary.vocabulary_path(str(tmp_path)), "w") as stream:
        stream.write("# a comment\n\n  pydantic  \nPOSTGRES\n")

    words = vocabulary.load(str(tmp_path))

    assert words == frozenset({"pydantic", "postgres"})


def test_remembering_an_existing_word_is_a_no_op(tmp_path):
    vocabulary.remember(str(tmp_path), "pydantic", log=log)
    firstWrite = os.path.getmtime(vocabulary.vocabulary_path(str(tmp_path)))

    assert vocabulary.remember(str(tmp_path), "PyDantic", log=log) is True
    assert vocabulary.load(str(tmp_path)) == frozenset({"pydantic"})
    assert os.path.getmtime(vocabulary.vocabulary_path(str(tmp_path))) == firstWrite


def test_an_unreadable_vocabulary_degrades_to_empty(tmp_path, monkeypatch):
    """*a damaged sidecar file must never stop a folder being created*"""
    vocabulary.remember(str(tmp_path), "pydantic", log=log)

    def denied(*args, **kwargs):
        raise PermissionError("nope")

    monkeypatch.setattr("builtins.open", denied)
    warnings = []
    monkeypatch.setattr(log, "warning", lambda msg, *args: warnings.append(msg))

    assert vocabulary.load(str(tmp_path), log=log) == frozenset()
    assert warnings


def test_a_failed_write_is_reported_but_never_raises(tmp_path, monkeypatch):
    """*the dismissal is simply offered again next run*"""
    def denied(*args, **kwargs):
        raise PermissionError("read-only filesystem")

    monkeypatch.setattr(vocabulary.tempfile, "mkstemp", denied)
    warnings = []
    monkeypatch.setattr(log, "warning", lambda msg, *args: warnings.append(msg))

    assert vocabulary.remember(str(tmp_path), "pydantic", log=log) is False
    assert warnings


def test_a_failed_write_leaves_no_temporary_file_behind(tmp_path, monkeypatch):
    realReplace = vocabulary.os.replace

    def failingReplace(source, target):
        raise OSError("disk full")

    monkeypatch.setattr(vocabulary.os, "replace", failingReplace)
    vocabulary.remember(str(tmp_path), "pydantic", log=log)
    monkeypatch.setattr(vocabulary.os, "replace", realReplace)

    leftovers = [name for name in os.listdir(tmp_path) if name.endswith(".tmp")]
    assert leftovers == []


def test_an_empty_or_blank_word_is_not_stored(tmp_path):
    assert vocabulary.remember(str(tmp_path), "   ", log=log) is False
    assert vocabulary.remember(str(tmp_path), "", log=log) is False
    assert not os.path.exists(vocabulary.vocabulary_path(str(tmp_path)))


def test_the_vocabulary_sits_outside_the_dropbox_ignored_index_folder(tmp_path):
    """*it must sync between machines - it records the user's jargon, not the machine's*"""
    pathToVocabulary = vocabulary.vocabulary_path(str(tmp_path))

    assert os.path.dirname(pathToVocabulary) == str(tmp_path)
    assert "00_INDEX" not in pathToVocabulary
