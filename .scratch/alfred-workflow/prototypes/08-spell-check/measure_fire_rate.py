"""HUMAN-TYPED CORPUS ONLY: SHALLOW, UNIQUE FOLDER TITLES UNDER THE AARDVARK ROOT."""

import os
import re
import statistics
import sys
import time

sys.path.insert(0, "/Users/Dave/git_repos/_packages_/python/aardvark-jd")

from aardvark_jd import spell_check

ROOT = "/Users/Dave/Dropbox/aardvark"
MAX_DEPTH = 3

_CODE = re.compile(r"^\d{2}(\.\d{2})?[_\-\s]+")
_NON_TITLE = re.compile(r"[^\w\s\-_.']+", re.UNICODE)

# A SILENTLY MISSING WORDLIST MAKES EVERY TOKEN LOOK CLEAN, WHICH IS
# INDISTINGUISHABLE FROM A GENUINE ZERO. FAIL LOUDLY INSTEAD.
WORDS = spell_check._load_words()
if not WORDS:
    sys.exit("wordlist failed to load - every number below would be a false zero")
print(f"wordlist: {len(WORDS)} words")

seen = {}
for dirpath, dirnames, filenames in os.walk(ROOT):
    relative = os.path.relpath(dirpath, ROOT)
    depth = 0 if relative == "." else relative.count(os.sep) + 1
    dirnames[:] = [name for name in dirnames if not name.startswith(".")]
    for name in dirnames:
        title = _NON_TITLE.sub(" ", _CODE.sub("", name)).strip()
        if title:
            seen.setdefault(title.lower(), (name, title))
    # NAMES COLLECTED ABOVE SIT AT depth + 1, SO STOP DESCENDING ONE LEVEL EARLY.
    if depth >= MAX_DEPTH - 1:
        dirnames[:] = []

titles = [seen[key] for key in sorted(seen)]
print(f"unique human-typed titles (depth 1-{MAX_DEPTH}): {len(titles)}")

fired = []
tokenCount = 0
flaggedTokens = 0

for name, title in titles:
    tokens = spell_check.tokenise(title)
    tokenCount += len(tokens)
    hits = []
    for token in tokens:
        suggestion = spell_check.suggest(token)
        if suggestion:
            flaggedTokens += 1
            hits.append((token, suggestion))
    if hits:
        fired.append((name, hits))

print(f"tokens checked: {tokenCount}")
print(f"tokens flagged: {flaggedTokens} ({100.0 * flaggedTokens / max(tokenCount, 1):.1f}%)")
print(f"titles firing:  {len(fired)} / {len(titles)} ({100.0 * len(fired) / max(len(titles), 1):.1f}%)")
print(f"titles with more than one suspect token: {sum(1 for _, hits in fired if len(hits) > 1)}")
print()
for name, hits in fired:
    pairs = ", ".join(f"{t} -> {s}" for t, s in hits)
    print(f"  {name!r}: {pairs}")

# LATENCY ACROSS THE WHOLE CORPUS, WARM. TIMING ONE TITLE SAYS NOTHING - `suggest`
# IS CHEAP ON A DICTIONARY HIT AND PAYS THE EDIT-DISTANCE SEARCH ONLY ON A MISS,
# SO THE SPREAD IS THE POINT.
timings = []
for name, title in titles:
    start = time.perf_counter()
    for token in spell_check.tokenise(title):
        spell_check.suggest(token)
    timings.append((time.perf_counter() - start) * 1000.0)

if timings:
    print()
    print(f"per-title check latency, warm, over {len(timings)} titles:")
    print(f"  min {min(timings):.4f} ms, median {statistics.median(timings):.4f} ms, "
          f"max {max(timings):.4f} ms")
