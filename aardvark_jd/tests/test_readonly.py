import yaml

from aardvark_jd import readonly


def test_with_connection_returns_none_when_no_system_is_configured(tmp_path):
    settingsPath = str(tmp_path / "settings.yaml")
    with open(settingsPath, "w") as stream:
        yaml.safe_dump({"version": 1, "system": {"name": None, "root_path": None}}, stream)
    result = readonly.with_connection(lambda conn: "unreachable", ["av", "cd", "-s", settingsPath])
    assert result is None


def test_with_connection_returns_none_when_the_index_cannot_be_found(tmp_path):
    """*a root with no `00_INDEX` folder fails inside connection setup, not inside `fn`*"""
    rootPath = tmp_path / "root"
    rootPath.mkdir()
    settingsPath = str(tmp_path / "settings.yaml")
    with open(settingsPath, "w") as stream:
        yaml.safe_dump({"version": 1, "system": {"name": "x", "root_path": str(rootPath)}}, stream)
    result = readonly.with_connection(lambda conn: "unreachable", ["av", "cd", "-s", settingsPath])
    assert result is None


def test_with_connection_returns_none_when_the_settings_file_is_missing(tmp_path):
    missingPath = str(tmp_path / "does-not-exist.yaml")
    result = readonly.with_connection(lambda conn: "unreachable", ["av", "cd", "-s", missingPath])
    assert result is None
