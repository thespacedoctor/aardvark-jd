"""
THE REJECTED CORPUS: EVERY FOLDER NAME UNDER THE AARDVARK ROOT, AT ANY DEPTH.

Kept because rejecting this corpus is part of the finding, and because the
multiple-suspect-token frequency quoted in the ticket 08 resolution comes from
here. It is dominated by machine-generated instrument data - seventy-odd
XSHOOTER_SLT_OBJ_* siblings - which nobody types into `add_*`, so its fire rate
describes a population the Alfred surface never sees. Use `measure_fire_rate.py`
for the number that matters.
"""

import os
import re
import sys

sys.path.insert(0, "/Users/Dave/git_repos/_packages_/python/aardvark-jd")

from aardvark_jd import spell_check

ROOT = "/Users/Dave/Dropbox/aardvark"

_CODE = re.compile(r"^\d{2}(\.\d{2})?[_\-\s]+")
_NON_TITLE = re.compile(r"[^\w\s\-_.']+", re.UNICODE)

# A SILENTLY MISSING WORDLIST MAKES EVERY TOKEN LOOK CLEAN, WHICH IS
# INDISTINGUISHABLE FROM A GENUINE ZERO. FAIL LOUDLY INSTEAD.
WORDS = spell_check._load_words()
if not WORDS:
    sys.exit("wordlist failed to load - every number below would be a false zero")
print(f"wordlist: {len(WORDS)} words")

# NO DEDUPLICATION AND NO DEPTH LIMIT - THAT IS THE WHOLE POINT OF THIS SWEEP,
# AND THE REASON ITS NUMBERS ARE NOT THE ONES THE DECISION RESTS ON.
names = []
for dirpath, dirnames, filenames in os.walk(ROOT):
    if any(part.startswith(".") for part in dirpath.split(os.sep)):
        continue
    for name in dirnames:
        if not name.startswith("."):
            names.append(name)

titles = []
for name in names:
    title = _NON_TITLE.sub(" ", _CODE.sub("", name)).strip()
    if title:
        titles.append((name, title))

print(f"folders: {len(names)}, titles after stripping: {len(titles)}")

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

multiple = [entry for entry in fired if len(entry[1]) > 1]

print(f"tokens checked: {tokenCount}")
print(f"tokens flagged: {flaggedTokens} ({100.0 * flaggedTokens / max(tokenCount, 1):.1f}%)")
print(f"titles firing:  {len(fired)} / {len(titles)} ({100.0 * len(fired) / max(len(titles), 1):.1f}%)")
print(f"titles with more than one suspect token: {len(multiple)} / {len(fired)}")
print()

# THE DISTINCT SUGGESTIONS, NOT EVERY REPEAT - ONE JARGON WORD REPEATED SEVENTY
# TIMES ACROSS SIBLING DATA FOLDERS IS ONE FALSE POSITIVE, NOT SEVENTY.
distinct = {}
for name, hits in fired:
    for token, suggestion in hits:
        key = (token.lower(), suggestion)
        distinct[key] = distinct.get(key, 0) + 1

print(f"distinct suspect tokens: {len(distinct)}")
for (token, suggestion), count in sorted(distinct.items(), key=lambda item: (-item[1], item[0])):
    print(f"  {token} -> {suggestion}  (x{count})")
