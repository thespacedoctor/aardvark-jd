"""RECALL: INJECT ONE REALISTIC TYPO PER REAL TITLE AND SEE HOW MANY THE CHECKER CATCHES."""

import os
import random
import re
import sys
import time

sys.path.insert(0, "/Users/Dave/git_repos/_packages_/python/aardvark-jd")

from aardvark_jd import spell_check

ROOT = "/Users/Dave/Dropbox/aardvark"
MAX_DEPTH = 3
SEED = 20260903

_CODE = re.compile(r"^\d{2}(\.\d{2})?[_\-\s]+")
_NON_TITLE = re.compile(r"[^\w\s\-_.']+", re.UNICODE)

# ADJACENT KEYS ON A QWERTY BOARD - REAL TYPOS ARE NEIGHBOUR SLIPS, NOT RANDOM LETTERS.
NEIGHBOURS = {
    "a": "qwsz", "b": "vghn", "c": "xdfv", "d": "serfcx", "e": "wsdr",
    "f": "drtgvc", "g": "ftyhbv", "h": "gyujnb", "i": "ujko", "j": "huikmn",
    "k": "jiolm", "l": "kop", "m": "njk", "n": "bhjm", "o": "iklp",
    "p": "ol", "q": "wa", "r": "edft", "s": "awedxz", "t": "rfgy",
    "u": "yhji", "v": "cfgb", "w": "qase", "x": "zsdc", "y": "tghu",
    "z": "asx",
}

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
            seen.setdefault(title.lower(), title)
    # NAMES COLLECTED ABOVE SIT AT depth + 1, SO STOP DESCENDING ONE LEVEL EARLY.
    if depth >= MAX_DEPTH - 1:
        dirnames[:] = []

# SORTED, NOT os.walk ORDER - THE SEED ONLY PINS THE RUN IF THE DRAW ORDER IS FIXED.
titles = sorted(seen.values())


def mistype(word, rng):
    """*one neighbour-key slip, transposition or dropped letter in `word`*"""
    # ONLY OFFER THE MUTATIONS THIS INDEX CAN ACTUALLY PERFORM, SO THE MIX IS NOT
    # SKEWED BY A transpose SILENTLY FALLING THROUGH TO A drop.
    for _ in range(20):
        index = rng.randrange(len(word))
        lowered = word[index].lower()
        kinds = ["drop"]
        if lowered in NEIGHBOURS:
            kinds.append("substitute")
        if index < len(word) - 1 and word[index] != word[index + 1]:
            kinds.append("transpose")
        kind = rng.choice(sorted(kinds))
        if kind == "substitute":
            typo = word[:index] + rng.choice(NEIGHBOURS[lowered]) + word[index + 1:]
        elif kind == "transpose":
            typo = word[:index] + word[index + 1] + word[index] + word[index + 2:]
        else:
            typo = word[:index] + word[index + 1:]
        if typo != word:
            return typo, kind
    return word, None


def inject(title, token, typo):
    """
    *put `typo` where `token` stands as a whole token, not merely as a substring*

    `spell_check._replace_token` guards its lookarounds against letters but not
    digits, so it would splice into the `backup` of `backup2024` before reaching
    a standalone `backup` later in the title. That lands the typo in a token
    `tokenise` then discards for containing a digit, and the trial is scored as a
    silent miss the checker never actually saw.
    """
    return re.sub(
        rf"(?<![A-Za-z0-9]){re.escape(token)}(?![A-Za-z0-9])", typo, title, count=1,
    )


rng = random.Random(SEED)

# ONLY TOKENS GENUINELY IN THE DICTIONARY. A TOKEN suggest() PASSES BECAUSE IT IS
# OUT-OF-VOCABULARY JARGON WITH NO DISTANCE-1 NEIGHBOUR CAN NEVER BE RECOVERED -
# suggest() ONLY EVER RETURNS DICTIONARY WORDS - SO INCLUDING THOSE WOULD PAD THE
# DENOMINATOR WITH UNWINNABLE TRIALS.
candidates = []
for title in titles:
    clean = sorted({t for t in spell_check.tokenise(title) if t.lower() in WORDS})
    if clean:
        candidates.append((title, clean))

print(f"unique human-typed titles (depth 1-{MAX_DEPTH}): {len(titles)}")
print(f"titles with a real dictionary token to corrupt: {len(candidates)}")

caught = 0
missed = []
byKind = {}
for title, clean in candidates:
    token = rng.choice(clean)
    typo, kind = mistype(token, rng)
    if kind is None:
        continue
    # SUBSTITUTE THE WHOLE TOKEN, NOT THE FIRST SUBSTRING MATCH - A PLAIN
    # str.replace CAN SPLICE THE TYPO INTO A LONGER WORD CONTAINING THE TOKEN.
    broken = inject(title, token, typo)
    if broken == title:
        continue
    hit = spell_check.suggest(typo) if typo in spell_check.tokenise(broken) else None
    tally = byKind.setdefault(kind, [0, 0])
    if hit == token.lower():
        caught += 1
        tally[0] += 1
    else:
        missed.append((title, token, typo, hit))
    tally[1] += 1

total = caught + len(missed)
print(f"typos injected: {total}")
print(f"caught with the right correction: {caught} ({100.0 * caught / max(total, 1):.1f}%)")
print(f"missed or wrongly corrected:      {len(missed)} ({100.0 * len(missed) / max(total, 1):.1f}%)")
print()

wrong = [m for m in missed if m[3] is not None]
silent = [m for m in missed if m[3] is None]
# DROPPING A LETTER FROM A SIX-CHARACTER WORD LEAVES FIVE, WHICH tokenise SKIPS.
# THE LENGTH FLOOR MAKES THIS WHOLE CLASS OF TYPO STRUCTURALLY INVISIBLE.
belowFloor = [m for m in silent if len(m[2]) < spell_check.MINIMUM_TOKEN_LENGTH]
print(f"  of {total}: {len(silent)} silent ({100.0 * len(silent) / max(total, 1):.1f}%), "
      f"{len(wrong)} wrong word ({100.0 * len(wrong) / max(total, 1):.1f}%)")
print(f"  of the {len(silent)} silent: {len(belowFloor)} were never checked at all - "
      f"the typo left the token under {spell_check.MINIMUM_TOKEN_LENGTH} characters")
print()
for kind in sorted(byKind):
    hit, seenCount = byKind[kind]
    print(f"  {kind}: {hit}/{seenCount} caught ({100.0 * hit / max(seenCount, 1):.1f}%)")
print()
for title, token, typo, hit in missed[:20]:
    print(f"  {token!r} -> typed {typo!r}: offered {hit!r}")

# LATENCY OF THE WHOLE CHECK ON ONE TITLE, WARM.
sample = candidates[0][0] if candidates else "aardvark notes"
spell_check.tokenise(sample)
start = time.perf_counter()
for _ in range(100):
    for token in spell_check.tokenise(sample):
        spell_check.suggest(token)
elapsed = (time.perf_counter() - start) / 100
print()
print(f"warm check latency, one title: {elapsed * 1000:.3f} ms")
