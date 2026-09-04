"""
TICKET 16: MEASURE THE THREE PROPOSED TUNING CHANGES AGAINST THE TICKET 08 CORPUS.

Sweeps the length floor and the tie-break rule together, because they interact:
a lower floor admits more deletion typos, and the deletion typo is exactly the
case the shortest-candidate tie-break gets wrong. Also counts how many suspect
tokens an -ize-tolerant wordlist would silence.

Reuses ticket 08's corpus construction and seed verbatim so the numbers are
comparable with `../08-spell-check/probe.md`.
"""

import os
import random
import re
import sys

sys.path.insert(0, "/Users/Dave/git_repos/_packages_/python/aardvark-jd")

from aardvark_jd import spell_check

ROOT = "/Users/Dave/Dropbox/aardvark"
MAX_DEPTH = 3
SEED = 20260903

_CODE = re.compile(r"^\d{2}(\.\d{2})?[_\-\s]+")
_NON_TITLE = re.compile(r"[^\w\s\-_.']+", re.UNICODE)
_SEPARATORS = re.compile(r"[_\-\s.]+")

NEIGHBOURS = {
    "a": "qwsz", "b": "vghn", "c": "xdfv", "d": "serfcx", "e": "wsdr",
    "f": "drtgvc", "g": "ftyhbv", "h": "gyujnb", "i": "ujko", "j": "huikmn",
    "k": "jiolm", "l": "kop", "m": "njk", "n": "bhjm", "o": "iklp",
    "p": "ol", "q": "wa", "r": "edft", "s": "awedxz", "t": "rfgy",
    "u": "yhji", "v": "cfgb", "w": "qase", "x": "zsdc", "y": "tghu",
    "z": "asx",
}

WORDS = spell_check._load_words()
if not WORDS:
    sys.exit("wordlist failed to load - every number below would be a false zero")


# ---------------------------------------------------------------- tokenising

def tokenise(title, floor):
    """*ticket 08's tokeniser, with the length floor as a parameter*"""
    return [
        token for token in _SEPARATORS.split(title or "")
        if len(token) >= floor and token.isalpha() and token.isascii()
    ]


# --------------------------------------------------------------- tie-breaks

def pick_shortest(token, candidates):
    """*the shipped rule: shortest candidate, ties broken alphabetically*"""
    return min(candidates, key=lambda word: (len(word), word))


def pick_longest(token, candidates):
    """*longest candidate, ties broken alphabetically*"""
    return min(candidates, key=lambda word: (-len(word), word))


def pick_same_first_letter(token, candidates):
    """*prefer a candidate starting with the token's first letter, then longest*"""
    first = token[:1].lower()
    return min(
        candidates,
        key=lambda word: (0 if word[:1] == first else 1, -len(word), word),
    )


def pick_deletion_first(token, candidates):
    """
    *assume a dropped letter before anything else*

    Ranks a candidate one longer than the token first (the typo dropped a
    letter), then equal length (a substitution or transposition), then shorter
    (the typo inserted one) - which is the rarest real slip and the shipped
    rule's first choice.
    """
    length = len(token)
    def rank(word):
        if len(word) == length + 1:
            return 0
        if len(word) == length:
            return 1
        return 2
    return min(candidates, key=lambda word: (rank(word), word))


TIE_BREAKS = (
    ("shortest (shipped)", pick_shortest),
    ("longest", pick_longest),
    ("same first letter", pick_same_first_letter),
    ("deletion first", pick_deletion_first),
)

FLOORS = (4, 5, 6, 7)


def suggest(token, words, tieBreak):
    """*`spell_check.suggest` with the tie-break as a parameter*"""
    lowered = token.lower()
    if lowered in words:
        return None
    candidates = spell_check._distance_one_variants(lowered) & words
    if not candidates:
        return None
    return tieBreak(lowered, candidates)


# ------------------------------------------------------------------- corpus

def collect_titles():
    """*ticket 08's depth-1-to-3 corpus of unique human-typed titles*"""
    seen = {}
    for dirpath, dirnames, filenames in os.walk(ROOT):
        relative = os.path.relpath(dirpath, ROOT)
        depth = 0 if relative == "." else relative.count(os.sep) + 1
        dirnames[:] = [name for name in dirnames if not name.startswith(".")]
        for name in dirnames:
            title = _NON_TITLE.sub(" ", _CODE.sub("", name)).strip()
            if title:
                seen.setdefault(title.lower(), title)
        if depth >= MAX_DEPTH - 1:
            dirnames[:] = []
    return sorted(seen.values())


def collect_wide_titles():
    """*every folder name at any depth - ticket 08's rejected corpus, kept for the -ize count*"""
    titles = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        if any(part.startswith(".") for part in dirpath.split(os.sep)):
            continue
        for name in dirnames:
            if name.startswith("."):
                continue
            title = _NON_TITLE.sub(" ", _CODE.sub("", name)).strip()
            if title:
                titles.append(title)
    return titles


def mistype(word, rng):
    """*ticket 08's injector, unchanged*"""
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
    """*replace `token` as a whole token, digits included in the guard*"""
    return re.sub(
        rf"(?<![A-Za-z0-9]){re.escape(token)}(?![A-Za-z0-9])", typo, title, count=1,
    )


# ------------------------------------------------------------------ measures

def measure_recall(titles, floor, tieBreak, words):
    """
    *inject one realistic typo per title and score the offer*

    The trial set is fixed by the seed and by ticket 08's floor-6 tokeniser, so
    every configuration is scored on the same typos rather than on a set the
    floor itself reshapes.
    """
    rng = random.Random(SEED)
    caught = wrong = silent = 0
    byKind = {}
    examples = []
    for title in titles:
        clean = sorted({t for t in tokenise(title, 6) if t.lower() in words})
        if not clean:
            continue
        token = rng.choice(clean)
        typo, kind = mistype(token, rng)
        if kind is None:
            continue
        broken = inject(title, token, typo)
        if broken == title:
            continue
        hit = suggest(typo, words, tieBreak) if typo in tokenise(broken, floor) else None
        tally = byKind.setdefault(kind, [0, 0])
        tally[1] += 1
        if hit == token.lower():
            caught += 1
            tally[0] += 1
        elif hit is None:
            silent += 1
        else:
            wrong += 1
            if len(examples) < 6:
                examples.append(f"{typo}->{hit} (wanted {token.lower()})")
    return {
        "trials": caught + wrong + silent,
        "caught": caught, "wrong": wrong, "silent": silent,
        "byKind": byKind, "examples": examples,
    }


def measure_fire(titles, floor, tieBreak, words):
    """*how often the checker speaks on real, untouched titles*"""
    firing = 0
    suspects = {}
    for title in titles:
        hits = [t for t in tokenise(title, floor) if suggest(t, words, tieBreak)]
        if hits:
            firing += 1
            for token in hits:
                suspects[token.lower()] = suggest(token, words, tieBreak)
    return firing, suspects


def americanised(words):
    """
    *the shipped -ise wordlist plus the -ize spellings it omits*

    Generated rather than downloaded: every `-ise`/`-isation`/`-yse` form in the
    list gets its American twin, which is the transformation the en_GB (as
    opposed to en_GB-ise) list encodes.
    """
    extra = set()
    for word in words:
        if word.endswith("ise"):
            extra.add(word[:-3] + "ize")
        elif word.endswith("ised"):
            extra.add(word[:-4] + "ized")
        elif word.endswith("ises"):
            extra.add(word[:-4] + "izes")
        elif word.endswith("ising"):
            extra.add(word[:-5] + "izing")
        elif word.endswith("isation"):
            extra.add(word[:-7] + "ization")
        elif word.endswith("isations"):
            extra.add(word[:-8] + "izations")
        elif word.endswith("iser"):
            extra.add(word[:-4] + "izer")
        elif word.endswith("isers"):
            extra.add(word[:-5] + "izers")
        elif word.endswith("yse"):
            extra.add(word[:-3] + "yze")
        elif word.endswith("ysed"):
            extra.add(word[:-4] + "yzed")
        elif word.endswith("yser"):
            extra.add(word[:-4] + "yzer")
        elif word.endswith("ysing"):
            extra.add(word[:-5] + "yzing")
    return frozenset(words | extra), len(extra)


# ---------------------------------------------------------------------- main

titles = collect_titles()
print(f"wordlist: {len(WORDS)} words")
print(f"unique human-typed titles (depth 1-{MAX_DEPTH}): {len(titles)}")
print()

print("=== recall and fire rate, by floor and tie-break ===")
print(f"{'floor':>5} {'tie-break':<20} {'right':>7} {'wrong':>7} {'silent':>7} "
      f"{'fires/title':>12} {'suspects':>9}")
for floor in FLOORS:
    for name, tieBreak in TIE_BREAKS:
        recall = measure_recall(titles, floor, tieBreak, WORDS)
        firing, suspects = measure_fire(titles, floor, tieBreak, WORDS)
        total = max(recall["trials"], 1)
        print(f"{floor:>5} {name:<20} "
              f"{100.0 * recall['caught'] / total:>6.1f}% "
              f"{100.0 * recall['wrong'] / total:>6.1f}% "
              f"{100.0 * recall['silent'] / total:>6.1f}% "
              f"{100.0 * firing / max(len(titles), 1):>11.1f}% "
              f"{len(suspects):>9}")
print()

print("=== by typo kind, floor 6 versus floor 5, shipped versus deletion-first ===")
for floor in (6, 5):
    for name, tieBreak in (("shortest (shipped)", pick_shortest), ("deletion first", pick_deletion_first)):
        recall = measure_recall(titles, floor, tieBreak, WORDS)
        kinds = " ".join(
            f"{kind}={100.0 * hit / max(seen, 1):.1f}%"
            for kind, (hit, seen) in sorted(recall["byKind"].items())
        )
        print(f"  floor {floor}, {name:<20} {kinds}")
        if recall["examples"]:
            print(f"    wrong offers: {', '.join(recall['examples'])}")
print()

print("=== what an -ize-tolerant wordlist silences ===")
wideTitles = collect_wide_titles()
tolerant, added = americanised(WORDS)
print(f"  folder names at any depth: {len(wideTitles)}")
print(f"  -ize forms added to the list: {added}")
for label, words in (("shipped en_GB-ise", WORDS), ("with -ize forms", tolerant)):
    firingNarrow, suspectsNarrow = measure_fire(titles, 6, pick_shortest, words)
    firingWide, suspectsWide = measure_fire(wideTitles, 6, pick_shortest, words)
    print(f"  {label:<20} narrow: {firingNarrow} titles / {len(suspectsNarrow)} tokens"
          f"   wide: {firingWide} titles / {len(suspectsWide)} tokens")
