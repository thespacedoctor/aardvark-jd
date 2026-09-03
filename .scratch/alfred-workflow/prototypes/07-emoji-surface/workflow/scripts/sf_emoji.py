#!/usr/bin/env python
"""PROTOTYPE - wayfinder ticket 07. THROWAWAY.

The emoji step of the mutating flow, built as a real Script Filter so it can
be felt on Alfred's interactive path.

Pattern under test: show the offline candidates INSTANTLY, spawn the Claude
call in a detached background process, and use Alfred's `rerun` to poll for
its result and slot it in at the top when it lands. If that works, the API
latency stops being blocking and the whole "will this feel slow" risk
dissolves. If it still feels bad, the fallback is to drop the Alfred emoji
surface entirely and let `set_emoji` / `repair_emoji` clean up afterwards.

Alfred does NOT filter these results (`alfredfiltersresults` is off) - this
script owns the ordering, because the whole point is re-ranking when the
Claude pick arrives.

Query forms:
  Photography                         just the title
  Photography | shoots and gear       title | description  (does the description move the pick?)
  Photography / camera film           anything after `/` is a free-text emoji search
"""
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from aardvark_jd import emoji_picker

HERE = Path(__file__).resolve().parent
RERUN_SECONDS = 0.3
# ALFRED RUNS SCRIPTS UNDER `/bin/zsh --no-rcs` WITH A SIX-ENTRY PATH AND NO
# LOGIN ENV, SO THE INTERPRETER PATH HAS TO BE HANDED IN EXPLICITLY.
WORKER_PY = os.environ.get("AARDVARK_PY") or sys.executable
CACHE_DIR = Path(
    os.environ.get("PROTO_CACHE")
    or os.environ.get("alfred_workflow_cache")
    or "/tmp/aardvark-tk07"
)


def key_for(title):
    return hashlib.sha1(title.lower().encode("utf-8")).hexdigest()[:12]


def offline_candidates(title, description, limit=6):
    """Up to `limit` distinct (emoji, matched-word) pairs from the offline index."""
    index = emoji_picker._get_keyword_index()
    seen = set()
    out = []
    for text in (title, description):
        for token in emoji_picker._tokenise(text or ""):
            for candidate in [token] + emoji_picker._singular_forms(token):
                found = index.get(candidate)
                if found and found not in seen:
                    seen.add(found)
                    out.append((found, token))
                    break
        if len(out) >= limit:
            break
    if not out:
        out.append((emoji_picker.FALLBACK_EMOJI, "fallback"))
    return out[:limit]


def emoji_search(term, limit=8):
    """Free-text search of the offline keyword index: prefix hits first."""
    term = term.strip().lower()
    if not term:
        return []
    words = [w for w in term.split() if w]
    index = emoji_picker._get_keyword_index()
    seen = set()
    hits = []
    for match_prefix in (True, False):
        for keyword, char in index.items():
            if char in seen:
                continue
            ok = any(keyword.startswith(w) for w in words) if match_prefix \
                else any(w in keyword for w in words)
            if ok:
                seen.add(char)
                hits.append((char, keyword))
                if len(hits) >= limit:
                    return hits
    return hits


def spawn_worker(title, description, key):
    """Fire the Claude call in a detached process, once per title."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    lock = CACHE_DIR / f"{key}.lock"
    try:
        fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(fd)
    except FileExistsError:
        return  # ANOTHER RERUN ALREADY STARTED IT
    subprocess.Popen(
        [WORKER_PY, str(HERE / "emoji_worker.py"), str(CACHE_DIR), key, title, description],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def candidate_item(emoji_char, note, *, valid=True):
    return {
        "uid": f"emoji:{emoji_char}",
        "title": f"{emoji_char}   {note}",
        "subtitle": f"↩ use {emoji_char}",
        "arg": emoji_char,
        "valid": valid,
        "variables": {"EMOJI": emoji_char, "EMOJI_SOURCE": note},
    }


def emit(items, *, rerun=False, variables=None):
    payload = {"skipknowledge": True, "items": items}
    if rerun:
        payload["rerun"] = RERUN_SECONDS
    if variables:
        # TOP-LEVEL `variables` ARE PASSED BACK IN AS ENV VARS ON THE NEXT
        # RERUN - THIS IS HOW THE WAIT-START TIME SURVIVES THE POLL LOOP.
        payload["variables"] = variables
    json.dump(payload, sys.stdout, ensure_ascii=False)


def spinner_rows(offline_rows, started):
    return [{
        "title": "Asking Claude for a suggestion…",
        "subtitle": f"waited {time.time() - started:0.1f}s   ·   pick an offline emoji below to skip the wait",
        "valid": False,
    }] + offline_rows


def main():
    raw = sys.argv[1] if len(sys.argv) > 1 else ""

    search_term = ""
    if "/" in raw:
        raw, search_term = raw.split("/", 1)
    if "|" in raw:
        title, description = (part.strip() for part in raw.split("|", 1))
    else:
        title, description = raw.strip(), ""

    if not title:
        emit([{
            "title": "Type a folder title",
            "subtitle": "the emoji step - offline picks show at once, Claude's arrives after",
            "valid": False,
        }])
        return

    key = key_for(title)
    result_file = CACHE_DIR / f"{key}.json"
    offline = offline_candidates(title, description)
    offline_rows = [candidate_item(e, f"{w}  (offline)") for e, w in offline]
    search_rows = [candidate_item(e, f"{kw}  (search: {search_term.strip()})")
                   for e, kw in emoji_search(search_term)]

    payload = None
    if result_file.exists():
        try:
            payload = json.loads(result_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            payload = None

    started = float(os.environ.get("WAIT_STARTED") or time.time())
    tail = search_rows or ([] if search_term else [{
        "title": "…or search: type  /  then a word",
        "subtitle": "e.g.  Photography / camera film   — a free-text emoji search",
        "valid": False,
    }])

    # FIRST SIGHT OF THIS TITLE: START THE CALL, SHOW OFFLINE + SPINNER.
    if payload is None:
        spawn_worker(title, description, key)
        emit(spinner_rows(offline_rows, started) + tail, rerun=True,
             variables={"WAIT_STARTED": str(started)})
        return

    if payload.get("status") == "pending":
        emit(spinner_rows(offline_rows, started) + tail, rerun=True,
             variables={"WAIT_STARTED": str(started)})
        return

    # DONE.
    elapsed = payload.get("elapsed_s", "?")
    if payload.get("source") == "claude":
        suggestion = payload["emoji"]
        rows = [candidate_item(suggestion, f"suggested by Claude  ·  {elapsed}s")]
        rows += [r for r in offline_rows if r["arg"] != suggestion]
        emit(rows + tail)
        return

    # CLAUDE RETURNED NOTHING - OFFLINE FALLBACK. SHOW IT AS VISIBLY DIFFERENT,
    # AND OFFER TO COMMIT WITH NO EMOJI AND REPAIR LATER.
    fallback = payload.get("emoji", emoji_picker.FALLBACK_EMOJI)
    rows = [{
        "uid": f"emoji:{fallback}",
        "title": f"{fallback}   Claude unavailable - offline pick",
        "subtitle": f"waited {elapsed}s, then fell back   ·   ↩ use {fallback}",
        "arg": fallback,
        "variables": {"EMOJI": fallback, "EMOJI_SOURCE": "offline-fallback"},
    }]
    rows += [r for r in offline_rows if r["arg"] != fallback]
    rows.append({
        "title": "Commit without an emoji",
        "subtitle": "create the folder now, fix the emoji later with `set_emoji` / `repair_emoji`",
        "arg": "",
        "variables": {"EMOJI": "", "EMOJI_SOURCE": "deferred"},
    })
    emit(rows + tail)


if __name__ == "__main__":
    main()
