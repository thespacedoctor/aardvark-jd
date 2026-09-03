#!/usr/bin/env python
"""PROTOTYPE - wayfinder ticket 07. THROWAWAY.

The background half of the "show offline instantly, swap in the Claude pick
when it lands" pattern. `sf_emoji.py` spawns this detached on the first run for
a title, then polls the result file via Alfred's `rerun`.

It calls `emoji_picker.suggest_emoji` - the real thing aardvark uses - times
it, and writes the outcome to <cachedir>/<key>.json:

    {"status": "done", "emoji": "...", "elapsed_s": 1.83, "source": "claude"}
    {"status": "done", "emoji": "...", "elapsed_s": 15.0, "source": "offline"}

"source" is "offline" whenever the Claude call returned nothing and
`suggest_emoji` fell back - that is the case the Alfred surface has to handle
without feeling broken.

Usage (called by sf_emoji.py, not by hand):

    emoji_worker.py <cachedir> <key> <title> [description]
"""
import json
import sys
import time
from pathlib import Path

from aardvark_jd import emoji_picker


def write(path, payload):
    """Atomic-ish write so a concurrent reader never sees a half file."""
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def main():
    cachedir, key, title = sys.argv[1], sys.argv[2], sys.argv[3]
    description = sys.argv[4] if len(sys.argv) > 4 else ""
    result = Path(cachedir) / f"{key}.json"

    write(result, {"status": "pending", "title": title})

    start = time.perf_counter()
    # THROWAWAY: CALL `suggest_emoji`, THEN ASK `pick_emoji` SEPARATELY SO WE
    # CAN TELL WHETHER THE CLAUDE CALL ACTUALLY CONTRIBUTED OR JUST FELL BACK.
    offline = emoji_picker.pick_emoji(title, description)
    claude = emoji_picker._suggest_via_claude(title, description)
    elapsed = time.perf_counter() - start

    if claude:
        payload = {"status": "done", "emoji": claude, "elapsed_s": round(elapsed, 2),
                   "source": "claude", "offline_emoji": offline}
    else:
        payload = {"status": "done", "emoji": offline, "elapsed_s": round(elapsed, 2),
                   "source": "offline", "offline_emoji": offline}
    write(result, payload)


if __name__ == "__main__":
    main()
