import plistlib

import pytest

from aardvark_jd.alfred import normalise


def _plist(objectUids=("C", "A", "B")):
    return {
        "bundleid": "com.thespacedoctor.aardvark-jd",
        "objects": [{"uid": uid, "type": "alfred.workflow.action.script", "config": {}} for uid in objectUids],
        "uidata": {uid: {"xpos": 10.0, "ypos": 20.0} for uid in objectUids},
        "connections": {},
    }


def test_objects_are_sorted_by_uid():
    normalised = normalise.normalise_plist(_plist())
    assert [entry["uid"] for entry in normalised["objects"]] == ["A", "B", "C"]


def test_uidata_is_left_exactly_as_alfred_wrote_it():
    """*stripping it would make Alfred re-lay out the canvas and destroy the visual editor*"""
    original = _plist()
    normalised = normalise.normalise_plist(original)
    assert normalised["uidata"] == original["uidata"]


def test_nothing_else_is_touched():
    original = _plist()
    normalised = normalise.normalise_plist(original)
    assert normalised["bundleid"] == original["bundleid"]
    assert set(normalised) == set(original)


def test_the_input_is_not_mutated():
    original = _plist()
    normalise.normalise_plist(original)
    assert [entry["uid"] for entry in original["objects"]] == ["C", "A", "B"]


def test_a_plist_with_no_objects_array_is_returned_unchanged():
    assert normalise.normalise_plist({"bundleid": "x"}) == {"bundleid": "x"}


def test_normalising_a_file_rewrites_it_in_sorted_order(tmp_path):
    plistPath = tmp_path / "info.plist"
    plistPath.write_bytes(plistlib.dumps(_plist()))

    changed = normalise.normalise_file(plistPath)

    assert changed is True
    assert [entry["uid"] for entry in plistlib.loads(plistPath.read_bytes())["objects"]] == ["A", "B", "C"]


def test_normalising_an_already_sorted_file_changes_nothing_and_says_so(tmp_path):
    plistPath = tmp_path / "info.plist"
    plistPath.write_bytes(plistlib.dumps(_plist(("A", "B", "C"))))
    before = plistPath.read_bytes()

    changed = normalise.normalise_file(plistPath)

    assert changed is False
    assert plistPath.read_bytes() == before


def test_the_shipped_workflow_plist_is_normalised():
    """*a guard on the committed file, so `make alfred-normalise` is never owed*"""
    from importlib.resources import files
    from pathlib import Path

    plistPath = Path(str(files("aardvark_jd"))) / "resources" / "alfred" / "info.plist"
    if not plistPath.exists():
        pytest.skip("the workflow is not shipped in this installation")

    plist = plistlib.loads(plistPath.read_bytes())
    uids = [entry["uid"] for entry in plist["objects"]]
    assert uids == sorted(uids)


def test_main_without_a_path_explains_itself_and_exits_non_zero(capsys):
    exitCode = normalise.main([])
    assert exitCode == 1
    assert "usage:" in capsys.readouterr().out


def test_main_reports_a_file_it_sorted(tmp_path, capsys):
    plistPath = tmp_path / "info.plist"
    plistPath.write_bytes(plistlib.dumps(_plist()))

    exitCode = normalise.main([str(plistPath)])

    assert exitCode == 0
    assert "sorted the `objects` array" in capsys.readouterr().out


def test_main_reports_a_file_that_was_already_sorted(tmp_path, capsys):
    plistPath = tmp_path / "info.plist"
    plistPath.write_bytes(plistlib.dumps(_plist(("A", "B", "C"))))

    exitCode = normalise.main([str(plistPath)])

    assert exitCode == 0
    assert "already sorted" in capsys.readouterr().out
