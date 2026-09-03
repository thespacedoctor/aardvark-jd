"""MEASURE THE PER-TITLE FIRE RATE OF spell_check ON THE LIVE INDEX."""

import sqlite3
import sys

sys.path.insert(0, "/Users/Dave/git_repos/_packages_/python/aardvark-jd")

from aardvark_jd import spell_check

DB = "/Users/Dave/Dropbox/aardvark/00_INDEX\U0001f5c2️/aardvark.db"

# A SILENTLY MISSING WORDLIST MAKES EVERY TOKEN LOOK CLEAN, WHICH IS
# INDISTINGUISHABLE FROM A GENUINE ZERO. FAIL LOUDLY INSTEAD.
WORDS = spell_check._load_words()
if not WORDS:
    sys.exit("wordlist failed to load - every number below would be a false zero")
print(f"wordlist: {len(WORDS)} words")

conn = sqlite3.connect(DB)
titles = []
for table in ("areas", "categories", "ids"):
    cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]
    if "title" not in cols:
        print(f"{table}: no title column, cols={cols}")
        continue
    for (title,) in conn.execute(f"SELECT title FROM {table}"):
        if title:
            titles.append((table, title))

print(f"titles: {len(titles)}")

firedTitles = []
tokenCount = 0
flaggedTokens = 0

for table, title in titles:
    tokens = spell_check.tokenise(title)
    tokenCount += len(tokens)
    hits = []
    for token in tokens:
        suggestion = spell_check.suggest(token)
        if suggestion:
            flaggedTokens += 1
            hits.append((token, suggestion))
    if hits:
        firedTitles.append((table, title, hits))

print(f"tokens checked: {tokenCount}")
print(f"tokens flagged: {flaggedTokens} ({100.0 * flaggedTokens / max(tokenCount, 1):.1f}%)")
print(f"titles firing:  {len(firedTitles)} / {len(titles)} ({100.0 * len(firedTitles) / max(len(titles), 1):.1f}%)")
print()
for table, title, hits in firedTitles:
    pairs = ", ".join(f"{t} -> {s}" for t, s in hits)
    print(f"  [{table}] {title!r}: {pairs}")
