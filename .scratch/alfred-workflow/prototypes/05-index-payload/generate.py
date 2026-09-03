#!/usr/bin/env python
"""
PROTOTYPE - throwaway. Answers wayfinder ticket 05: does shipping the whole
aardvark index to Alfred as one payload hold up at realistic scale?

Generates a synthetic aardvark index at a chosen entity count, following the
Johnny Decimal shape (3 domains -> areas -> categories -> IDs), and emits it
two ways:

  --as cli-json   the `aardvark fd --json` envelope decided in ticket 03
  --as alfred     the Alfred Script Filter `items` payload the workflow ships

Field shapes and string lengths are modelled on the live schema (db.py) and
doc_links.py URL forms, so the byte counts are realistic rather than invented.

No database, no network. Deterministic given --seed.
"""

import argparse
import base64
import hashlib
import json
import random
import sys

DOMAINS = [("areas", "A"), ("resources", "R"), ("projects", "P")]

# REALISTIC TOKEN POOLS - short, human, JD-ish. NOT exhaustive; enough to make
# titles/descriptions vary in length the way real ones do.
_ADJ = ["annual", "personal", "shared", "legal", "medical", "archived", "draft",
        "active", "external", "internal", "quarterly", "regional", "core"]
_NOUN = ["records", "correspondence", "invoices", "contracts", "reports", "notes",
         "photos", "receipts", "policies", "manuals", "templates", "research",
         "budgets", "minutes", "proposals", "inventory", "credentials", "backups"]
_TOPIC = ["health", "finance", "property", "vehicles", "insurance", "travel",
          "education", "career", "family", "hardware", "software", "garden",
          "kitchen", "utilities", "pets", "hobbies", "taxes", "pensions"]

_ROOT = "/Users/Dave/My Life"
_DOMAIN_FOLDER = {
    "areas": "03_AREAS\U0001f9ed",
    "resources": "04_RESOURCES\U0001f4da",
    "projects": "02_PROJECTS\U0001f680",
}
_EMOJI_POOL = ["\U0001f3e5", "\U0001fa7a", "\U0001f4b0", "\U0001f697", "\U0001f3e1",
               "✈️", "\U0001f393", "\U0001f4bc", "\U0001f46a", "\U0001f5a5️"]


def _synthetic_hook_id(abs_path):
    digest = hashlib.blake2b(abs_path.encode("utf-8"), digest_size=8).digest()
    num = int.from_bytes(digest, "big")
    alpha = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    out = []
    while len(out) < 9:
        num, r = divmod(num, 62)
        out.append(alpha[r])
    return "".join(reversed(out))


def _finder_url(abs_path):
    parent, name = abs_path.rsplit("/", 1)
    hint = "/".join(parent.split("/")[-2:])
    b64 = base64.b64encode(hint.encode("utf-8")).decode("ascii")
    enc = "".join(c if c.isalnum() and c.isascii()
                  else "".join(f"%{b:02X}" for b in c.encode("utf-8")) for c in name)
    return f"hook://file/{_synthetic_hook_id(abs_path)}?p={b64}&n={enc}"


def _slug(text):
    return text.replace(" ", "_")


def _title(rng):
    shape = rng.random()
    if shape < 0.4:
        return f"{rng.choice(_TOPIC).capitalize()}"
    if shape < 0.8:
        return f"{rng.choice(_ADJ).capitalize()} {rng.choice(_NOUN)}"
    return f"{rng.choice(_ADJ).capitalize()} {rng.choice(_TOPIC)} {rng.choice(_NOUN)}"


def _description(rng):
    n = rng.randint(0, 22)
    if n == 0:
        return ""
    words = [rng.choice(_ADJ + _NOUN + _TOPIC) for _ in range(n)]
    return " ".join(words).capitalize()


def _urls(rng, entity_type, abs_path, row_key):
    # MODELLED ON doc_links.py + the live *_links tables. A fraction of entities
    # are unsynced (real systems have partial mirror coverage).
    synced = rng.random() < 0.85
    craft = f"https://craft.example/space/{_rand_hex(rng, 12)}/doc/{_rand_hex(rng, 20)}" if synced else None
    todoist = (f"https://app.todoist.com/app/project/{_rand_hex(rng, 10)}"
               if synced and entity_type in ("area", "category", "id") and rng.random() < 0.9 else None)
    drive = (f"https://drive.google.com/drive/folders/{_rand_b64(rng, 33)}"
             if synced and rng.random() < 0.9 else None)
    dropbox = (f"https://www.dropbox.com/scl/fo/{_rand_hex(rng, 15)}/{_slug(_title(rng))}?rlkey={_rand_hex(rng, 22)}&dl=0"
               if synced and rng.random() < 0.8 else None)
    return {
        "finder": _finder_url(abs_path),
        "craft": craft,
        "todoist": todoist,
        "drive": drive,
        "dropbox": dropbox,
    }


def _rand_hex(rng, n):
    return "".join(rng.choice("0123456789abcdef") for _ in range(n))


def _rand_b64(rng, n):
    return "".join(rng.choice("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_") for _ in range(n))


def build_index(target_count, seed):
    """Build a flat list of entity records, in index order, ~target_count long."""
    rng = random.Random(seed)
    entities = []

    # DISTRIBUTE target_count ACROSS THE TREE. IDs DOMINATE; areas/categories
    # are a small fixed overhead per the JD shape.
    per_domain = max(1, target_count // 3)

    for domain, letter in DOMAINS:
        domain_folder = f"{_ROOT}/{_DOMAIN_FOLDER[domain]}"
        # ~9 areas per domain (00-09 reserved)
        area_count = min(9, max(1, per_domain // 200 + 1))
        ids_budget = per_domain - area_count  # rough
        cats_per_area = min(9, max(1, ids_budget // (area_count * 15) + 1))
        ids_per_cat = max(0, ids_budget // max(1, area_count * cats_per_area))

        for a in range(area_count):
            decade_start = (a + 1) * 10
            decade_end = decade_start + 9
            code = f"{letter}{decade_start}-{decade_end}"
            title = f"{rng.choice(_TOPIC).capitalize()}"
            emoji = rng.choice(_EMOJI_POOL)
            folder = f"{domain_folder}/{letter}{decade_start}_{decade_end}_{_slug(title.lower())}{emoji}"
            row_key = str(len(entities) + 1)
            entities.append(_record("area", domain, code, title, _description(rng),
                                    emoji, folder, row_key, rng))
            for c in range(1, cats_per_area + 1):
                ac = decade_start + c
                ccode = f"{letter}{ac}"
                ctitle = _title(rng)
                cemoji = rng.choice(_EMOJI_POOL)
                cfolder = f"{folder}/{letter}{ac}_{_slug(ctitle.lower())}{cemoji}"
                crow = str(len(entities) + 1)
                entities.append(_record("category", domain, ccode, ctitle, _description(rng),
                                        cemoji, cfolder, crow, rng))
                for i in range(10, 10 + ids_per_cat):
                    icode = f"{letter}{ac}.{i}"
                    ititle = _title(rng)
                    ifolder = f"{cfolder}/{letter}{ac}.{i}_{_slug(ititle.lower())}"
                    irow = str(len(entities) + 1)
                    entities.append(_record("id", domain, icode, ititle, _description(rng),
                                            "", ifolder, irow, rng))
    return entities


def _record(entity_type, domain, code, title, description, emoji, folder, row_key, rng):
    return {
        "id": f"{domain}:{code}",
        "row_key": row_key,
        "type": entity_type,
        "domain": domain,
        "code": code,
        "title": title,
        "description": description,
        "emoji": emoji,
        "folder_path": folder,
        "archived": False,
        "urls": _urls(rng, entity_type, folder, row_key),
    }


def cli_json_envelope(entities):
    return {
        "aardvark_json": 1,
        "system": {
            "name": "My Life",
            "root_path": _ROOT,
            "generated_at": "2026-09-03T12:00:00Z",
        },
        "entities": entities,
    }


def _match_string(e, match_includes_description):
    parts = [e["code"], e["title"]]
    # PATH SEGMENTS BELOW THE ROOT
    parts.extend(s for s in e["folder_path"][len(_ROOT):].split("/") if s)
    if match_includes_description and e["description"]:
        parts.append(e["description"])
    return " ".join(parts)


def _title_line(e):
    if e["emoji"]:
        return f"{e['code']}  {e['emoji']}  {e['title']}"
    return f"{e['code']}  {e['title']}"


def alfred_items(entities, match_includes_description, lean=False):
    """
    lean=False  - every mirror URL lives in its own `mods` block as `arg`,
                  with the shared discriminator repeated per ticket 01's
                  "variables replace wholesale" rule. Zero downstream lookup.
    lean=True   - one `variables.urls` object per item, no `mods`. The
                  downstream object resolves the chosen URL from the cached
                  payload. Smaller, but couples the workflow to the payload.
    """
    items = []
    for e in entities:
        item = {
            "uid": e["id"],
            "title": _title_line(e),
            "subtitle": e["folder_path"],
            "match": _match_string(e, match_includes_description),
            "arg": e["folder_path"],
        }
        if lean:
            item["variables"] = {"entity_id": e["id"], "urls": json.dumps(e["urls"], ensure_ascii=False)}
        else:
            eid = e["id"]
            item["variables"] = {"entity_id": eid}
            item["mods"] = {
                key: {"subtitle": label, "arg": e["urls"][svc] or "",
                      "variables": {"entity_id": eid, "open": svc}}
                for key, label, svc in (
                    ("cmd", "Open in Craft", "craft"),
                    ("alt", "Open in Todoist", "todoist"),
                    ("ctrl", "Open in Drive", "drive"),
                    ("shift", "Reveal in Finder", "finder"),
                    ("fn", "Copy Dropbox link", "dropbox"),
                )
            }
        items.append(item)
    out = {"items": items, "skipknowledge": True}
    if not _NO_CACHE:
        out["cache"] = {"seconds": 3600, "loosereload": True}
    return out


_NO_CACHE = False


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--count", type=int, default=5000)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--as", dest="form", choices=["cli-json", "alfred"], default="alfred")
    p.add_argument("--match-description", action="store_true",
                   help="alfred form: fold description into the match string")
    p.add_argument("--lean", action="store_true",
                   help="alfred form: one urls object per item, no per-mod duplication")
    p.add_argument("--no-cache", action="store_true",
                   help="alfred form: omit the cache block (measure the cold path)")
    p.add_argument("--pretty", action="store_true")
    args = p.parse_args()

    global _NO_CACHE
    _NO_CACHE = args.no_cache
    entities = build_index(args.count, args.seed)
    if args.form == "cli-json":
        payload = cli_json_envelope(entities)
    else:
        payload = alfred_items(entities, args.match_description, lean=args.lean)

    indent = 2 if args.pretty else None
    sep = None if args.pretty else (",", ":")
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=indent, separators=sep)
    sys.stdout.write("\n")
    print(f"# {len(entities)} entities", file=sys.stderr)


if __name__ == "__main__":
    main()
