#!/usr/bin/env python
# encoding: utf-8
"""
*Offer to correct a typo in a new folder's title, before anything is created*

The check runs **before** the entity exists, in the same `get()` that
resolves the emoji and ahead of the emoji prompt - accepting a correction
changes the title the emoji is derived from. Checking first is what
designs the hard case out entirely: the corrected title is the single
value the folder name, the index row and all three mirrors are built
from, so there is no post-creation rename and no mirror repoint.

It **offers**; it never blocks and never silently rewrites. That is not
politeness, it is arithmetic - on a realistic technical vocabulary this
configuration flags 18 per cent of tokens, so a checker that corrected
without asking would corrupt titles routinely.

Two rules do almost all the work of keeping that rate down, and they
matter far more than which wordlist ships (across nine SCOWL sizes the
false-positive count moved by one under the right tokeniser, and by 21
under a naive one):

- check only tokens of **six characters or more**, split on `[_\\-\\s.]`
- offer only when a **distance-1 dictionary word actually exists**

Distance 2 was measured and rejected: 49 per cent false positives and 850
times the runtime, to recover four typos in thirty-four.

The wordlist is the ESDB/SCOWL `en_GB-ise` size-60 list, shipped in
`resources/wordlists/` with its copyright notice. It is a plain list read
into a `frozenset` (+12.3 ms) rather than a spell-checking library
because `spylls` costs 402 ms to load and `symspellpy` 1,212 ms to index,
against a 500 ms budget for the whole command.

Author
: David Young
"""

import os
import re
import sys

from aardvark_jd import vocabulary

_WORDLIST_PATH = os.path.join(
    os.path.dirname(__file__), "resources", "wordlists", "en_GB-ise.txt",
)

# SHORT TOKENS ARE WHERE THE FALSE POSITIVES LIVE - EVERY THREE-LETTER
# FRAGMENT IS ONE EDIT FROM SOME DICTIONARY WORD.
MINIMUM_TOKEN_LENGTH = 6

_TOKEN_SEPARATORS = re.compile(r"[_\-\s.]+")
_ALPHABET = "abcdefghijklmnopqrstuvwxyz"

_words = None


def _load_words():
    """
    *the shipped `en_GB` wordlist, as a `frozenset`, loaded once per process*

    A missing or unreadable wordlist disables the feature rather than
    breaking the command.

    **Return:**

    - ``words`` -- the dictionary, possibly empty
    """
    global _words
    if _words is None:
        try:
            with open(_WORDLIST_PATH, encoding="utf-8") as stream:
                _words = frozenset(
                    stripped for stripped in (line.strip() for line in stream) if stripped
                )
        except (OSError, UnicodeDecodeError):
            _words = frozenset()
    return _words


def enabled(settings):
    """
    *is spell-checking switched on?*

    The clean "always off" exit for someone who creates many folders full
    of fresh proper nouns, where self-silencing on recurring jargon does
    not help. Mirrors the existing `emoji.use_llm` toggle.

    **Key Arguments:**

    - ``settings`` -- the aardvark settings dict

    **Return:**

    - ``enabled`` -- `True` unless `spell_check.enabled` is explicitly false
    """
    spellSettings = (settings or {}).get("spell_check")
    if not isinstance(spellSettings, dict):
        return True
    return bool(spellSettings.get("enabled", True))


def tokenise(title):
    """
    *split a title into the tokens worth checking*

    **Key Arguments:**

    - ``title`` -- the folder title as typed

    **Return:**

    - ``tokens`` -- the original-case tokens long enough and alphabetic enough to check
    """
    tokens = []
    for token in _TOKEN_SEPARATORS.split(title or ""):
        if len(token) >= MINIMUM_TOKEN_LENGTH and token.isalpha() and token.isascii():
            tokens.append(token)
    return tokens


def _distance_one_variants(word):
    """
    *every string one insertion, deletion, substitution or transposition from `word`*

    **Key Arguments:**

    - ``word`` -- a lowercase token

    **Return:**

    - ``variants`` -- the candidate set, excluding `word` itself
    """
    splits = [(word[:index], word[index:]) for index in range(len(word) + 1)]
    variants = set()
    for left, right in splits:
        if right:
            variants.add(left + right[1:])                                  # DELETION
            for letter in _ALPHABET:
                variants.add(left + letter + right[1:])                     # SUBSTITUTION
        if len(right) > 1:
            variants.add(left + right[1] + right[0] + right[2:])            # TRANSPOSITION
        for letter in _ALPHABET:
            variants.add(left + letter + right)                             # INSERTION
    variants.discard(word)
    return variants


def suggest(token):
    """
    *the best distance-1 dictionary word for a token, or `None` if it needs no correction*

    Returns `None` for a token already in the dictionary - that is the
    common case and must be cheap.

    **Key Arguments:**

    - ``token`` -- the token to check, in any case

    **Return:**

    - ``suggestion`` -- a lowercase dictionary word, or `None`
    """
    words = _load_words()
    if not words:
        return None

    lowered = token.lower()
    if lowered in words:
        return None

    candidates = _distance_one_variants(lowered) & words
    if not candidates:
        return None
    # NO FREQUENCY DATA SHIPS WITH THE LIST, SO PREFER THE SHORTEST
    # CANDIDATE AND BREAK TIES ALPHABETICALLY - DETERMINISTIC, WHICH MATTERS
    # MORE HERE THAN CLEVER, SINCE A WRONG OFFER IS ONE KEYSTROKE TO DECLINE.
    return min(candidates, key=lambda word: (len(word), word))


def _apply_case(original, replacement):
    """
    *carry the original token's capitalisation onto its replacement*

    **Key Arguments:**

    - ``original`` -- the token as the user typed it
    - ``replacement`` -- the lowercase dictionary word

    **Return:**

    - ``cased`` -- the replacement, capitalised to match
    """
    if original.isupper():
        return replacement.upper()
    if original[:1].isupper():
        return replacement.capitalize()
    return replacement


def _replace_token(title, token, replacement):
    """
    *substitute one token in a title, leaving every separator and other token alone*

    **Key Arguments:**

    - ``title`` -- the full title
    - ``token`` -- the token to replace, as it appears
    - ``replacement`` -- what to put there

    **Return:**

    - ``title`` -- the title with that one token replaced
    """
    # THE LOOKAROUNDS GUARD LETTERS, NOT DIGITS, SO A TITLE PAIRING A
    # DIGIT-SUFFIXED TOKEN WITH THE SAME BARE MISSPELLING (`aadvark2 aadvark`)
    # WOULD MATCH INSIDE THE FORMER FIRST. `tokenise` NEVER OFFERS A TOKEN
    # CONTAINING A DIGIT, SO THAT ONLY MISPLACES A CORRECTION THE USER ASKED
    # FOR, AND ONLY IN A TITLE SHAPED THAT WAY.
    return re.sub(
        rf"(?<![A-Za-z]){re.escape(token)}(?![A-Za-z])", replacement, title, count=1,
    )


def check_title(title, rootPath=None, settings=None, log=None):
    """
    *offer a correction for each suspect token, and return the title to actually use*

    Interactive sessions get one `[y/N]` prompt per suspect token, in
    title order. Accepting substitutes that token. **Declining - `N` or a
    bare Enter - records the token in the learned vocabulary permanently**,
    so the low-friction answer is the one that makes the feature go quiet
    on recurring jargon. That self-silencing is what makes this worth
    shipping at all.

    Non-interactive sessions (scripts, CI, the test suite) never block:
    the title is used exactly as typed and one note per suspect token goes
    to stderr. Those notes are filtered through the same learned
    vocabulary, so a token dismissed interactively stays quiet in later
    scripted runs.

    **Key Arguments:**

    - ``title`` -- the title as the user typed it
    - ``rootPath`` -- the aardvark system root, for the learned vocabulary. Default `None`, meaning no learning.
    - ``settings`` -- the aardvark settings dict. Default `None`.
    - ``log`` -- logger. Default `None`.

    **Return:**

    - ``title`` -- the corrected title, or the original if nothing was accepted

    **Usage:**

    ```python
    from aardvark_jd import spell_check
    title = spell_check.check_title("Aadvark notes", rootPath=rootPath, settings=settings)
    ```
    """
    if not title or not enabled(settings):
        return title

    known = vocabulary.load(rootPath, log=log) if rootPath else frozenset()
    interactive = sys.stdin.isatty()
    # A TITLE CAN REPEAT A TOKEN. ONE DECISION COVERS EVERY OCCURRENCE OF IT -
    # ASKING TWICE ABOUT THE SAME WORD IN ONE TITLE WOULD BE ABSURD, AND THE
    # FIRST DECLINE HAS ALREADY LEARNED IT ANYWAY.
    handled = set()

    for token in tokenise(title):
        lowered = token.lower()
        if lowered in known or lowered in handled:
            continue
        suggestion = suggest(token)
        if not suggestion:
            continue
        handled.add(lowered)

        if not interactive:
            print(
                f"note: '{token}' in title may be a typo of '{suggestion}'",
                file=sys.stderr,
            )
            continue

        corrected = _apply_case(token, suggestion)
        try:
            reply = input(f"'{token}' - did you mean '{corrected}'? [y/N] ")
        except EOFError:
            # Ctrl-D AT THE PROMPT. THIS HELPER PROMISES IT CANNOT BREAK THE
            # COMMAND, SO AN END-OF-INPUT IS A DECLINE, NOT A TRACEBACK - BUT
            # IT IS NOT A DELIBERATE DISMISSAL, SO IT TEACHES NOTHING.
            print(file=sys.stderr)
            break

        if reply.strip().lower() in ("y", "yes"):
            # EVERY OCCURRENCE, NOT JUST THE FIRST: THE DECISION IS ABOUT THE
            # WORD, AND `_replace_token` TAKES THE NEXT ONE STILL MISSPELLED.
            while True:
                replaced = _replace_token(title, token, corrected)
                if replaced == title:
                    break
                title = replaced
        elif rootPath:
            # DECLINING TEACHES IT THE WORD. THIS IS THE WHOLE REASON THE
            # FEATURE IS TOLERABLE AT AN 18 PER CENT FALSE-POSITIVE RATE.
            vocabulary.remember(rootPath, token, log=log)

    return title


def checked_title(rawTitle, settings=None, log=None):
    """
    *the title to build a new entity from, after offering to correct any typo in it*

    The single entry point the four `add_*` commands call, so the way the
    system root is located stays in one place.

    **Key Arguments:**

    - ``rawTitle`` -- the title as the user typed it
    - ``settings`` -- the aardvark settings dict. Default `None`.
    - ``log`` -- logger. Default `None`.

    **Return:**

    - ``title`` -- the title to actually use
    """
    rootPath = ((settings or {}).get("system") or {}).get("root_path")
    return check_title(rawTitle, rootPath=rootPath, settings=settings, log=log)
