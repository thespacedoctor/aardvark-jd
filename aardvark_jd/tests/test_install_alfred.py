import json
import logging
import os

import pytest

from aardvark_jd.install_alfred import install_alfred


@pytest.fixture
def logger():
    return logging.getLogger("test_install_alfred")


@pytest.fixture
def alfredSupport(tmp_path):
    """*a fake `~/Library/Application Support/Alfred` with a real preferences folder*"""
    supportPath = tmp_path / "Application Support" / "Alfred"
    supportPath.mkdir(parents=True)
    preferencesPath = tmp_path / "Dropbox" / "Alfred.alfredpreferences"
    (preferencesPath / "workflows").mkdir(parents=True)
    (supportPath / "prefs.json").write_text(
        json.dumps({"current": str(preferencesPath)}), encoding="utf-8",
    )
    return supportPath, preferencesPath


@pytest.fixture
def consoleScript(tmp_path):
    """*a fake environment whose `bin` holds an executable `aardvark`*"""
    binPath = tmp_path / "env" / "bin"
    binPath.mkdir(parents=True)
    interpreterPath = binPath / "python3.14"
    interpreterPath.write_text("#!/bin/sh\n", encoding="utf-8")
    consoleScriptPath = binPath / "aardvark"
    consoleScriptPath.write_text("#!/bin/sh\n", encoding="utf-8")
    consoleScriptPath.chmod(0o755)
    return interpreterPath, consoleScriptPath


def _install(logger, alfredSupport, consoleScript, tmp_path, **overrides):
    supportPath, _preferencesPath = alfredSupport
    interpreterPath, _consoleScriptPath = consoleScript
    arguments = {
        "log": logger,
        "executable": str(interpreterPath),
        "alfredSupportPath": str(supportPath),
        "pointerPath": str(tmp_path / "pointer" / "alfred-binary-path"),
    }
    arguments.update(overrides)
    return install_alfred(**arguments)


def test_the_pointer_is_written_with_the_console_script_not_the_interpreter(
    logger, alfredSupport, consoleScript, tmp_path,
):
    """*there is no `__main__.py`, so the interpreter alone cannot launch anything*"""
    _interpreterPath, consoleScriptPath = consoleScript
    pointerPath = tmp_path / "pointer" / "alfred-binary-path"

    _install(logger, alfredSupport, consoleScript, tmp_path).get()

    assert pointerPath.read_text(encoding="utf-8").strip() == str(consoleScriptPath)


def test_the_workflow_is_deployed_as_a_symlink_into_alfreds_workflows_folder(
    logger, alfredSupport, consoleScript, tmp_path,
):
    _supportPath, preferencesPath = alfredSupport

    _install(logger, alfredSupport, consoleScript, tmp_path).get()

    workflowPath = preferencesPath / "workflows" / "aardvark-jd"
    assert workflowPath.is_symlink()
    assert (workflowPath / "info.plist").exists()


def test_re_running_is_idempotent_and_reports_the_symlink_unchanged(
    logger, alfredSupport, consoleScript, tmp_path,
):
    _supportPath, preferencesPath = alfredSupport
    workflowPath = preferencesPath / "workflows" / "aardvark-jd"

    _install(logger, alfredSupport, consoleScript, tmp_path).get()
    firstTarget = os.readlink(workflowPath)
    messages = _install(logger, alfredSupport, consoleScript, tmp_path).get()

    assert os.readlink(workflowPath) == firstTarget
    assert any("unchanged" in message for message in messages)


def test_a_symlink_pointing_elsewhere_is_replaced_because_nothing_is_lost(
    logger, alfredSupport, consoleScript, tmp_path,
):
    _supportPath, preferencesPath = alfredSupport
    strayTarget = tmp_path / "somewhere-else"
    strayTarget.mkdir()
    workflowPath = preferencesPath / "workflows" / "aardvark-jd"
    workflowPath.symlink_to(strayTarget)

    _install(logger, alfredSupport, consoleScript, tmp_path).get()

    assert workflowPath.is_symlink()
    assert os.readlink(workflowPath) != str(strayTarget)


def test_a_real_directory_from_an_imported_bundle_is_never_touched(
    logger, alfredSupport, consoleScript, tmp_path,
):
    """*an imported `.alfredworkflow` is the user's own copy, and overwriting it would lose their edits*"""
    _supportPath, preferencesPath = alfredSupport
    workflowPath = preferencesPath / "workflows" / "aardvark-jd"
    workflowPath.mkdir()
    (workflowPath / "info.plist").write_text("imported", encoding="utf-8")
    pointerPath = tmp_path / "pointer" / "alfred-binary-path"

    messages = _install(logger, alfredSupport, consoleScript, tmp_path).get()

    assert not workflowPath.is_symlink()
    assert (workflowPath / "info.plist").read_text(encoding="utf-8") == "imported"
    # THE POINTER IS STILL WRITTEN: IT IS NEEDED ON EVERY MACHINE, INCLUDING
    # ONE THAT INSTALLED BY DOUBLE-CLICKING THE EXPORTED BUNDLE.
    assert pointerPath.exists()
    assert any("will not auto-update" in message for message in messages)


def test_no_alfred_at_all_is_a_clean_failure_not_a_traceback(logger, consoleScript, tmp_path):
    interpreterPath, _consoleScriptPath = consoleScript

    with pytest.raises(ValueError) as excInfo:
        install_alfred(
            log=logger,
            executable=str(interpreterPath),
            alfredSupportPath=str(tmp_path / "no-alfred-here"),
            pointerPath=str(tmp_path / "pointer" / "alfred-binary-path"),
        ).get()

    assert "Alfred is not installed" in str(excInfo.value)


def test_an_unreadable_prefs_json_is_reported_differently_and_names_the_file(
    logger, alfredSupport, consoleScript, tmp_path,
):
    """*a present Alfred with a broken `prefs.json` is a real anomaly, not an absent Alfred*"""
    supportPath, _preferencesPath = alfredSupport
    (supportPath / "prefs.json").write_text("{ not json", encoding="utf-8")

    with pytest.raises(ValueError) as excInfo:
        _install(logger, alfredSupport, consoleScript, tmp_path).get()

    message = str(excInfo.value)
    assert "prefs.json" in message
    assert "Alfred is not installed" not in message


def test_a_prefs_json_without_current_is_the_same_anomaly(
    logger, alfredSupport, consoleScript, tmp_path,
):
    supportPath, _preferencesPath = alfredSupport
    (supportPath / "prefs.json").write_text(json.dumps({"other": "thing"}), encoding="utf-8")

    with pytest.raises(ValueError) as excInfo:
        _install(logger, alfredSupport, consoleScript, tmp_path).get()

    assert "prefs.json" in str(excInfo.value)


def test_the_default_preferences_path_is_never_a_fallback(
    logger, alfredSupport, consoleScript, tmp_path,
):
    """*`Alfred.alfredpreferences` beside `prefs.json` exists but is vestigial, so writing there would appear to succeed*"""
    supportPath, _preferencesPath = alfredSupport
    (supportPath / "Alfred.alfredpreferences" / "workflows").mkdir(parents=True)
    (supportPath / "prefs.json").unlink()
    (supportPath / "prefs.plist").write_text("", encoding="utf-8")

    with pytest.raises(ValueError):
        _install(logger, alfredSupport, consoleScript, tmp_path).get()

    assert not (supportPath / "Alfred.alfredpreferences" / "workflows" / "aardvark-jd").exists()


def test_uninstall_removes_the_symlink_and_the_pointer_and_nothing_else(
    logger, alfredSupport, consoleScript, tmp_path,
):
    _supportPath, preferencesPath = alfredSupport
    workflowPath = preferencesPath / "workflows" / "aardvark-jd"
    pointerPath = tmp_path / "pointer" / "alfred-binary-path"

    _install(logger, alfredSupport, consoleScript, tmp_path).get()
    target = os.path.realpath(workflowPath)

    _install(logger, alfredSupport, consoleScript, tmp_path, uninstall=True).get()

    assert not workflowPath.exists()
    assert not workflowPath.is_symlink()
    assert not pointerPath.exists()
    # THE REPO COPY THE LINK POINTED AT IS UNTOUCHED.
    assert os.path.exists(os.path.join(target, "info.plist"))


def test_uninstall_is_idempotent(logger, alfredSupport, consoleScript, tmp_path):
    _install(logger, alfredSupport, consoleScript, tmp_path, uninstall=True).get()
    messages = _install(logger, alfredSupport, consoleScript, tmp_path, uninstall=True).get()

    assert messages


def test_uninstall_never_deletes_an_imported_real_directory(
    logger, alfredSupport, consoleScript, tmp_path,
):
    _supportPath, preferencesPath = alfredSupport
    workflowPath = preferencesPath / "workflows" / "aardvark-jd"
    workflowPath.mkdir()
    (workflowPath / "info.plist").write_text("imported", encoding="utf-8")

    _install(logger, alfredSupport, consoleScript, tmp_path, uninstall=True).get()

    assert (workflowPath / "info.plist").read_text(encoding="utf-8") == "imported"
