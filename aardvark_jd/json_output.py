#!/usr/bin/env python
# encoding: utf-8
"""
*Render aardvark's internal JSON response contract*

The JSON contract is internal and unstable. Nothing outside this repository may depend on it. It may be reshaped without a deprecation cycle, and the `aardvark_json` integer is bumped on any breaking change.

Author
: David Young
"""

from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from typing import Any

from aardvark_jd import codes, doc_links, folders

AARDVARK_JSON_VERSION = 1
NO_SYSTEM_KIND = "no_system"

_EXHAUSTION_KINDS = {
    folders.DomainExhaustedError: "domain_exhausted",
    folders.CategoryExhaustedError: "category_exhausted",
    folders.IdExhaustedError: "id_exhausted",
}


def _entity_code(row: Mapping[str, Any]) -> str:
    if row["entity_type"] == "area":
        return codes.format_area_code(
            row["domain"], row["decade_start"], row["decade_end"]
        )
    if row["entity_type"] == "category":
        return codes.format_category_code(row["domain"], row["ac_number"])
    if row["entity_type"] == "id":
        return codes.format_id_code(row["domain"], row["ac_number"], row["item_number"])
    raise ValueError(f"Unknown entity type: {row['entity_type']}")


def entity_record(
    row: Mapping[str, Any], links: Mapping[str, str | None]
) -> dict[str, Any]:
    """
    *render one live entity as an internal JSON record*

    **Key Arguments:**

    - ``row`` -- an entity row from `db.entities_with_links`
    - ``links`` -- the entity's Craft, Todoist, Drive and Dropbox URLs

    **Return:**

    - ``record`` -- the entity's JSON-ready record
    """
    code = _entity_code(row)
    return {
        "id": f"{row['domain']}:{code}",
        "row_key": str(row["row_key"]),
        "type": row["entity_type"],
        "domain": row["domain"],
        "code": code,
        "title": row["title"],
        "description": row["description"],
        "emoji": row["emoji"] or "",
        "folder_path": row["folder_path"],
        "archived": False,
        "urls": {
            "finder": doc_links.hookmark_url(row["folder_path"]),
            "craft": links.get("craft"),
            "todoist": links.get("todoist"),
            "drive": links.get("drive"),
            "dropbox": links.get("dropbox"),
        },
    }


def entity_records(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """
    *render live entity rows while extracting their joined mirror URLs*

    **Key Arguments:**

    - ``rows`` -- rows from `db.entities_with_links`

    **Return:**

    - ``records`` -- the JSON-ready live entity records
    """
    return [
        entity_record(
            row,
            {
                "craft": row["craft_url"],
                "todoist": row["todoist_url"],
                "drive": row["gdrive_url"],
                "dropbox": row["dropbox_url"],
            },
        )
        for row in rows
    ]


def archived_record(row: Mapping[str, Any]) -> dict[str, Any]:
    """
    *render one archived entity and its mirror-link snapshot as an internal JSON record*

    **Key Arguments:**

    - ``row`` -- a row from the `archived_entities` table

    **Return:**

    - ``record`` -- the archived entity's JSON-ready record
    """
    return {
        "id": f"{row['domain']}:{row['code']}",
        "row_key": str(row["entity_key"]),
        "type": row["entity_type"],
        "domain": row["domain"],
        "code": row["code"],
        "title": row["title"],
        "description": row["description"],
        "emoji": row["emoji"] or "",
        "folder_path": row["archived_path"],
        "archived": True,
        "urls": {
            "finder": None,
            "craft": row["craft_url"],
            "todoist": row["todoist_url"],
            "drive": row["gdrive_url"],
            "dropbox": row["dropbox_url"],
        },
    }


def read_envelope(
    system: Mapping[str, Any],
    entities: list[dict[str, Any]],
    archived: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    *wrap rendered entities and system metadata in the versioned read response*

    **Key Arguments:**

    - ``system`` -- rendered system metadata
    - ``entities`` -- rendered live entity records
    - ``archived`` -- rendered archived entity records. Default `None`, which omits the field.

    **Return:**

    - ``envelope`` -- the versioned JSON-ready read response
    """
    return {
        "aardvark_json": AARDVARK_JSON_VERSION,
        "system": dict(system),
        "entities": list(entities),
        **({"archived": list(archived)} if archived is not None else {}),
    }


def system_block(
    settings: Mapping[str, Any],
    version: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """
    *build system metadata for a versioned read response*

    **Key Arguments:**

    - ``settings`` -- the aardvark settings dict
    - ``version`` -- the installed aardvark package version
    - ``now`` -- the generation time. Default `None`, which uses the current UTC time.

    **Return:**

    - ``system`` -- the JSON-ready system metadata
    """
    systemSettings = settings.get("system") or {}
    currentTime = now or datetime.now(timezone.utc)
    generatedAt = (
        currentTime.astimezone(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )
    return {
        "name": systemSettings.get("name"),
        "root_path": systemSettings.get("root_path"),
        "generated_at": generatedAt,
        "version": version,
    }


def result_envelope(
    action: str,
    entity: Mapping[str, Any] | None = None,
    entities: list[dict[str, Any]] | None = None,
    **fields: Any,
) -> dict[str, Any]:
    """
    *wrap a command result in the versioned JSON response contract*

    **Key Arguments:**

    - ``action`` -- the command action that produced the result
    - ``entity`` -- the single affected entity. Default `None`.
    - ``entities`` -- the affected entity list for bulk actions. Default `None`.
    - ``fields`` -- action-specific result fields

    **Return:**

    - ``envelope`` -- the versioned JSON-ready result response
    """
    if (entity is None) == (entities is None):
        raise ValueError("Exactly one of entity or entities must be supplied")
    entityField = (
        {"entity": dict(entity)}
        if entity is not None
        else {"entities": [dict(item) for item in entities or []]}
    )
    return {
        "aardvark_json": AARDVARK_JSON_VERSION,
        "result": {
            "action": action,
            **entityField,
            **fields,
            "warnings": fields.get("warnings", []),
        },
    }


def _error_kind(error: Exception) -> str:
    for errorType, kind in _EXHAUSTION_KINDS.items():
        if isinstance(error, errorType):
            return kind
    if isinstance(error, KeyError):
        return "not_found"
    if isinstance(error, ValueError):
        # THE CLI USES BARE VALUEERRORS FOR BOTH CASES, SO THESE EXACT SUBSTRINGS ARE PINNED BY TESTS AND A REWORD MUST FAIL LOUDLY.
        if "not found" in str(error):
            return "not_found"
        if "has not been synced to" in str(error):
            return "not_synced"
        return "value_error"
    return "error"


def error_envelope_for_kind(kind: str, message: str) -> dict[str, Any]:
    """
    *render a failure that carries no exception to classify*

    The "no aardvark system found" exit is a plain early return rather than a raise, so its kind is stated rather than inferred.

    **Key Arguments:**

    - ``kind`` -- the stable machine token, e.g. `NO_SYSTEM_KIND`
    - ``message`` -- the human-readable message

    **Return:**

    - ``envelope`` -- the versioned JSON-ready error response
    """
    return {
        "aardvark_json": AARDVARK_JSON_VERSION,
        "error": {"kind": kind, "message": message},
    }


def error_envelope(error: Exception) -> dict[str, Any]:
    """
    *render an exception as a stable machine kind and human-readable message*

    Exception types without a specific mapping use the stable fallback kind `"error"`.

    **Key Arguments:**

    - ``error`` -- the exception to render

    **Return:**

    - ``envelope`` -- the versioned JSON-ready error response
    """
    return {
        "aardvark_json": AARDVARK_JSON_VERSION,
        "error": {
            "kind": _error_kind(error),
            "message": str(error),
        },
    }
