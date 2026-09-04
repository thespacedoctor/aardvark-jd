import sys
from datetime import datetime, timezone

import pytest

from aardvark_jd import folders, json_output
from aardvark_jd.__version__ import __version__ as PACKAGE_VERSION


def test_entity_record_builds_an_area_record(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    row = {
        "entity_type": "area",
        "row_key": "42",
        "domain": "areas",
        "decade_start": 10,
        "decade_end": 19,
        "ac_number": None,
        "item_number": None,
        "title": "Health",
        "description": "Wellbeing",
        "emoji": "🏥",
        "folder_path": "/root/A10_19_health🏥",
    }
    links = {
        "craft": "https://craft.example/area",
        "todoist": "https://todoist.example/area",
        "drive": "https://drive.example/area",
        "dropbox": "https://dropbox.example/area",
    }

    record = json_output.entity_record(row, links)

    assert record == {
        "id": "areas:A10-19",
        "row_key": "42",
        "type": "area",
        "domain": "areas",
        "code": "A10-19",
        "title": "Health",
        "description": "Wellbeing",
        "emoji": "🏥",
        "folder_path": "/root/A10_19_health🏥",
        "archived": False,
        "urls": {
            "finder": None,
            "craft": "https://craft.example/area",
            "todoist": "https://todoist.example/area",
            "drive": "https://drive.example/area",
            "dropbox": "https://dropbox.example/area",
        },
    }


def test_entity_record_builds_a_category_record(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    row = {
        "entity_type": "category",
        "row_key": "43",
        "domain": "resources",
        "decade_start": None,
        "decade_end": None,
        "ac_number": 11,
        "item_number": None,
        "title": "Manuals",
        "description": "Reference manuals",
        "emoji": "📘",
        "folder_path": "/root/R11_manuals📘",
    }

    record = json_output.entity_record(row, {})

    assert record["id"] == "resources:R11"
    assert record["row_key"] == "43"
    assert record["type"] == "category"
    assert record["domain"] == "resources"
    assert record["code"] == "R11"
    assert record["title"] == "Manuals"
    assert record["description"] == "Reference manuals"
    assert record["emoji"] == "📘"
    assert record["folder_path"] == "/root/R11_manuals📘"
    assert record["archived"] is False
    assert record["urls"] == {
        "finder": None,
        "craft": None,
        "todoist": None,
        "drive": None,
        "dropbox": None,
    }


def test_entity_record_builds_an_id_record(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    row = {
        "entity_type": "id",
        "row_key": "44",
        "domain": "projects",
        "decade_start": None,
        "decade_end": None,
        "ac_number": 11,
        "item_number": 10,
        "title": "Launch",
        "description": "",
        "emoji": "",
        "folder_path": "/root/P11.10_launch",
    }

    record = json_output.entity_record(row, {})

    assert record["id"] == "projects:P11.10"
    assert record["row_key"] == "44"
    assert record["type"] == "id"
    assert record["domain"] == "projects"
    assert record["code"] == "P11.10"
    assert record["title"] == "Launch"
    assert record["description"] == ""
    assert record["emoji"] == ""
    assert record["folder_path"] == "/root/P11.10_launch"
    assert record["archived"] is False
    assert record["urls"] == {
        "finder": None,
        "craft": None,
        "todoist": None,
        "drive": None,
        "dropbox": None,
    }


def test_entity_record_preserves_a_blank_stored_emoji(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    row = {
        "entity_type": "area",
        "row_key": "42",
        "domain": "areas",
        "decade_start": 10,
        "decade_end": 19,
        "title": "Health",
        "description": "",
        "emoji": "",
        "folder_path": "/root/A10_19_health",
    }

    record = json_output.entity_record(row, {})

    assert record["emoji"] == ""


def test_entity_record_builds_the_finder_url_from_the_folder_path(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    row = {
        "entity_type": "area",
        "row_key": "42",
        "domain": "areas",
        "decade_start": 10,
        "decade_end": 19,
        "title": "Health",
        "description": "",
        "emoji": "🏥",
        "folder_path": "/root/A10_19_health🏥",
    }

    record = json_output.entity_record(row, {})

    assert record["urls"]["finder"].startswith("hook://file/")


def test_entity_record_id_is_stable_across_row_key_title_and_emoji_changes(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    originalRow = {
        "entity_type": "category",
        "row_key": "42",
        "domain": "areas",
        "ac_number": 11,
        "title": "Doctors",
        "description": "",
        "emoji": "🩺",
        "folder_path": "/root/A11_doctors🩺",
    }
    changedRow = {
        **originalRow,
        "row_key": "999",
        "title": "Medical specialists",
        "emoji": "⚕️",
    }

    originalId = json_output.entity_record(originalRow, {})["id"]
    changedId = json_output.entity_record(changedRow, {})["id"]

    assert originalId == changedId == "areas:A11"


def test_entity_records_extracts_mirror_links_from_each_row(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    row = {
        "entity_type": "id",
        "row_key": "44",
        "domain": "areas",
        "decade_start": None,
        "decade_end": None,
        "ac_number": 11,
        "item_number": 10,
        "title": "Cardiologist",
        "description": "",
        "emoji": "",
        "folder_path": "/root/A11.10_cardiologist",
        "craft_url": "https://craft.example/id",
        "todoist_url": "https://todoist.example/id",
        "gdrive_url": "https://drive.example/id",
        "dropbox_url": "https://dropbox.example/id",
    }

    records = json_output.entity_records([row])

    assert records[0]["urls"] == {
        "finder": None,
        "craft": "https://craft.example/id",
        "todoist": "https://todoist.example/id",
        "drive": "https://drive.example/id",
        "dropbox": "https://dropbox.example/id",
    }


def test_archived_record_uses_the_archived_path_and_snapshot_links():
    row = {
        "entity_type": "category",
        "entity_key": "43",
        "domain": "resources",
        "code": "R11",
        "title": "Manuals",
        "description": "Reference manuals",
        "emoji": "📘",
        "original_path": "/root/R11_manuals📘",
        "archived_path": "/root/archive/R11_manuals📘",
        "craft_url": "https://craft.example/category",
        "todoist_url": "https://todoist.example/category",
        "gdrive_url": "https://drive.example/category",
        "dropbox_url": "https://dropbox.example/category",
    }

    record = json_output.archived_record(row)

    assert record == {
        "id": "resources:R11",
        "row_key": "43",
        "type": "category",
        "domain": "resources",
        "code": "R11",
        "title": "Manuals",
        "description": "Reference manuals",
        "emoji": "📘",
        "folder_path": "/root/archive/R11_manuals📘",
        "archived": True,
        "urls": {
            "finder": None,
            "craft": "https://craft.example/category",
            "todoist": "https://todoist.example/category",
            "drive": "https://drive.example/category",
            "dropbox": "https://dropbox.example/category",
        },
    }


def test_read_envelope_omits_archived_when_not_requested():
    system = {"name": "My Life"}
    entities = [{"id": "areas:A10-19"}]

    envelope = json_output.read_envelope(system, entities)

    assert envelope == {
        "aardvark_json": 1,
        "system": {"name": "My Life"},
        "entities": [{"id": "areas:A10-19"}],
    }
    assert "archived" not in envelope


def test_read_envelope_includes_an_empty_archived_list_when_requested():
    envelope = json_output.read_envelope({}, [], archived=[])

    assert envelope == {
        "aardvark_json": 1,
        "system": {},
        "entities": [],
        "archived": [],
    }


def test_system_block_uses_nested_settings_and_an_injected_utc_time():
    settings = {
        "system": {
            "name": "My Life",
            "root_path": "/Users/Dave/My Life",
        }
    }
    now = datetime(2026, 9, 3, 12, 0, tzinfo=timezone.utc)

    system = json_output.system_block(settings, PACKAGE_VERSION, now=now)

    assert system == {
        "name": "My Life",
        "root_path": "/Users/Dave/My Life",
        "generated_at": "2026-09-03T12:00:00Z",
        "version": PACKAGE_VERSION,
    }
    assert system["generated_at"].endswith("Z")


def test_result_envelope_wraps_one_entity_with_default_warnings():
    entity = {"id": "areas:A11.10"}

    envelope = json_output.result_envelope("add_id", entity=entity)

    assert envelope == {
        "aardvark_json": 1,
        "result": {
            "action": "add_id",
            "entity": {"id": "areas:A11.10"},
            "warnings": [],
        },
    }
    assert "sync" not in envelope["result"]
    assert "summary" not in envelope["result"]


def test_result_envelope_uses_entities_for_a_bulk_result():
    entities = [{"id": "areas:A10-19"}, {"id": "areas:A11"}]

    result = json_output.result_envelope("repair_emoji", entities=entities)["result"]

    assert result["entities"] == entities
    assert "entity" not in result
    assert result["warnings"] == []


def test_result_envelope_rejects_both_entity_shapes():
    with pytest.raises(ValueError, match="Exactly one of entity or entities"):
        json_output.result_envelope("repair_emoji", entity={}, entities=[])


def test_result_envelope_rejects_a_missing_entity_shape():
    with pytest.raises(ValueError, match="Exactly one of entity or entities"):
        json_output.result_envelope("add_id")


def test_result_envelope_includes_supplied_optional_fields():
    optionalFields = {
        "emoji_source": "offline",
        "corrections": [{"from": "cardilogist", "to": "cardiologist"}],
        "suggestions": [
            {"token": "cardilogist", "index": 1, "suggested": "cardiologist"}
        ],
        "sync": "backgrounded",
        "template_used": "blank",
        "summary": {"updated": 1},
        "drift": [{"mirror": "craft"}],
        "warnings": ["Craft is unavailable"],
    }

    result = json_output.result_envelope("add_id", entity={}, **optionalFields)[
        "result"
    ]

    for fieldName, value in optionalFields.items():
        assert result[fieldName] == value


@pytest.mark.parametrize(
    "error, expectedKind",
    [
        (folders.DomainExhaustedError("No domains remain"), "domain_exhausted"),
        (folders.CategoryExhaustedError("No categories remain"), "category_exhausted"),
        (folders.IdExhaustedError("No IDs remain"), "id_exhausted"),
    ],
)
def test_error_envelope_maps_exhaustion_errors(error, expectedKind):
    envelope = json_output.error_envelope(error)

    assert envelope == {
        "aardvark_json": 1,
        "error": {
            "kind": expectedKind,
            "message": str(error),
        },
    }


@pytest.mark.parametrize(
    "error",
    [
        KeyError("A99"),
        ValueError("Entity not found: A99"),
    ],
)
def test_error_envelope_maps_lookup_failures_to_not_found(error):
    envelope = json_output.error_envelope(error)

    assert envelope["error"] == {
        "kind": "not_found",
        "message": str(error),
    }


def test_error_envelope_maps_open_craft_unsynced_message_to_not_synced():
    error = ValueError(
        "'A11.10 Cardiologist' has not been synced to craft, todoist or google drive yet - "
        "run `aardvark craft_sync`, `aardvark todoist_sync` and/or `aardvark gdrive_sync` first"
    )

    envelope = json_output.error_envelope(error)

    assert envelope["error"] == {
        "kind": "not_synced",
        "message": str(error),
    }


def test_error_envelope_maps_other_value_errors_to_value_error():
    error = ValueError("The reference is malformed")

    envelope = json_output.error_envelope(error)

    assert envelope["error"] == {
        "kind": "value_error",
        "message": "The reference is malformed",
    }


def test_no_system_kind_is_exposed_for_the_future_cli_early_exit():
    assert json_output.NO_SYSTEM_KIND == "no_system"


def test_error_envelope_uses_error_as_the_unknown_exception_fallback():
    error = RuntimeError("Unexpected failure")

    envelope = json_output.error_envelope(error)

    assert envelope["error"] == {
        "kind": "error",
        "message": "Unexpected failure",
    }


def test_error_envelope_for_kind_states_a_kind_no_exception_carries():
    """*the "no system" exit has no exception to classify, so the kind is passed in*"""
    envelope = json_output.error_envelope_for_kind(
        json_output.NO_SYSTEM_KIND, "no aardvark system found",
    )
    assert envelope == {
        "aardvark_json": json_output.AARDVARK_JSON_VERSION,
        "error": {"kind": "no_system", "message": "no aardvark system found"},
    }
