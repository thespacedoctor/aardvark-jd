#!/usr/bin/env python
# encoding: utf-8
"""
*Pick an appropriate emoji for a folder name from its title/description*

Author
: David Young
"""

import re
import sys

import emoji

FALLBACK_EMOJI = "📁"

# THE CLAUDE MODEL AND REQUEST SHAPE USED BY `suggest_emoji`. THINKING IS LEFT
# AT ITS OPUS 5 DEFAULT (ADAPTIVE) - DISABLING IT CAN LEAK `<thinking>` TAGS
# INTO THE VISIBLE REPLY - AND `low` EFFORT KEEPS THIS TRIVIAL CLASSIFICATION
# FAST. `max_tokens` CAPS THINKING + REPLY TOGETHER, SO IT NEEDS HEADROOM.
CLAUDE_MODEL = "claude-opus-5"
CLAUDE_MAX_TOKENS = 1024
CLAUDE_EFFORT = "low"
# NO RETRIES, AND A TIGHT TIMEOUT: THE OFFLINE PICKER IS AN INSTANT, EQUALLY
# VALID ANSWER, SO FALLING BACK BEATS MAKING SOMEONE WAIT OUT A SECOND ATTEMPT
# AT AN INTERACTIVE PROMPT.
CLAUDE_TIMEOUT_SECONDS = 15.0
CLAUDE_MAX_RETRIES = 0

_SUGGESTER_SYSTEM_PROMPT = (
    "You choose a single emoji to label a folder in a personal knowledge-filing "
    "system. Pick the emoji that best captures the folder's subject, favouring "
    "common, instantly-recognisable emoji over obscure ones. Reply with exactly "
    "one emoji character and nothing else: no words, no punctuation, no "
    "explanation, no code fences."
)

_STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "for", "to", "in", "on", "at",
    "with", "my", "our", "your",
}

_keywordIndex = None


def _build_keyword_index():
    """
    *build a keyword -> emoji lookup from `emoji.EMOJI_DATA`'s CLDR short names*

    Only fully-qualified emoji are indexed (skips skin-tone/component
    modifiers), and the first emoji seen for a given keyword wins, so
    shorter/more canonical entries (which sort first in `EMOJI_DATA`)
    take priority over obscure variants.

    **Return:**

    - ``keywordIndex`` -- a dict mapping lowercase keyword -> emoji character
    """
    keywordIndex = {}
    for character, data in emoji.EMOJI_DATA.items():
        if data.get("status") != emoji.STATUS["fully_qualified"]:
            continue
        names = [data.get("en", "")] + data.get("alias", [])
        for name in names:
            for keyword in name.strip(":").split("_"):
                keyword = keyword.lower()
                if keyword and keyword not in keywordIndex:
                    keywordIndex[keyword] = character
    return keywordIndex


def _get_keyword_index():
    """
    *lazily build and cache the keyword -> emoji index*

    **Return:**

    - ``keywordIndex`` -- the cached keyword -> emoji index
    """
    global _keywordIndex
    if _keywordIndex is None:
        _keywordIndex = _build_keyword_index()
    return _keywordIndex


def _tokenise(text):
    """
    *split free text into lowercase, stopword-free keyword tokens*

    **Key Arguments:**

    - ``text`` -- the free text to tokenise

    **Return:**

    - ``tokens`` -- a list of lowercase keyword tokens
    """
    words = re.findall(r"[A-Za-z]+", text.lower())
    return [word for word in words if word not in _STOPWORDS]


def _singular_forms(word):
    """
    *candidate singular spellings for a word, most-specific rule first*

    The CLDR short names behind the keyword index are singular, so plural
    titles ("Films", "Templates") miss an otherwise-available emoji. Exact
    matches are always tried before these candidates, so this only ever
    adds coverage.

    **Key Arguments:**

    - ``word`` -- the lowercase word to singularise

    **Return:**

    - ``candidates`` -- a list of candidate singular spellings
    """
    candidates = []
    if len(word) > 4 and word.endswith("ies"):
        candidates.append(word[:-3] + "y")
    if len(word) > 3 and word.endswith("es"):
        candidates.append(word[:-2])
    if len(word) > 2 and word.endswith("s") and not word.endswith("ss"):
        candidates.append(word[:-1])
    return candidates


def pick_emoji(title, description=""):
    """
    *pick an appropriate emoji for a folder from its title and description, offline*

    Looks up each word of ``title`` in turn against the `emoji` package's
    keyword index (trying the word as written before its singular forms),
    then falls back to ``description`` if nothing in the title matched, and
    finally to :py:data:`FALLBACK_EMOJI`.

    This is the offline picker, used as the fallback whenever
    :py:func:`suggest_emoji` cannot reach the Claude API.

    **Key Arguments:**

    - ``title`` -- the folder's title
    - ``description`` -- the folder's description. Default `""`.

    **Return:**

    - ``pickedEmoji`` -- the picked emoji character

    **Usage:**

    ```python
    from aardvark_jd import emoji_picker
    pickedEmoji = emoji_picker.pick_emoji("Hospital", "Appointments and visits")
    ```
    """
    keywordIndex = _get_keyword_index()

    for text in (title, description):
        for token in _tokenise(text or ""):
            for candidate in [token] + _singular_forms(token):
                if candidate in keywordIndex:
                    return keywordIndex[candidate]

    return FALLBACK_EMOJI


def suggest_emoji(title, description="", settings=None, log=None):
    """
    *suggest an emoji for a folder, asking Claude first and falling back offline*

    Asks the Claude API for a single emoji, validates that the reply really
    is one emoji, and degrades to :py:func:`pick_emoji` on any problem at
    all - the `anthropic` package missing, no credentials configured, no
    network, a policy refusal, or a reply that is not a single emoji.

    **Key Arguments:**

    - ``title`` -- the folder's title
    - ``description`` -- the folder's description. Default `""`.
    - ``settings`` -- the aardvark settings dict, used to honour `emoji: use_llm: false`. Default `None`.
    - ``log`` -- logger. Default `None`.

    **Return:**

    - ``suggestedEmoji`` -- the suggested emoji character

    **Usage:**

    ```python
    from aardvark_jd import emoji_picker
    suggestedEmoji = emoji_picker.suggest_emoji("Doctors", "GP and specialists", settings=settings, log=log)
    ```
    """
    if llm_enabled(settings):
        suggestedEmoji = _suggest_via_claude(title, description, log=log)
        if suggestedEmoji:
            return suggestedEmoji

    return pick_emoji(title, description)


def resolve_emoji(title, description="", chosenEmoji=None, settings=None, log=None):
    """
    *settle on the emoji for a new folder, from an explicit choice, a prompt, or the suggester*

    Resolution order:

    1. ``chosenEmoji`` given (the `--emoji` flag) - used verbatim, with no API call and no prompt
    2. an interactive session - the suggestion is shown for the user to accept or replace
    3. a non-interactive session - the suggestion is accepted silently

    **Key Arguments:**

    - ``title`` -- the folder's title
    - ``description`` -- the folder's description. Default `""`.
    - ``chosenEmoji`` -- an emoji supplied on the command-line. Default `None`.
    - ``settings`` -- the aardvark settings dict. Default `None`.
    - ``log`` -- logger. Default `None`.

    **Return:**

    - ``resolvedEmoji`` -- the emoji to append to the folder name

    **Usage:**

    ```python
    from aardvark_jd import emoji_picker
    resolvedEmoji = emoji_picker.resolve_emoji("Doctors", "GP and specialists", chosenEmoji="🩺")
    ```
    """
    if chosenEmoji:
        return validate_chosen_emoji(chosenEmoji)

    suggestedEmoji = suggest_emoji(title, description, settings=settings, log=log)

    if not sys.stdin.isatty():
        return suggestedEmoji

    print(f"Suggested emoji for '{title}': {suggestedEmoji}")
    while True:
        reply = input("Press Enter to accept, or type a replacement emoji: ").strip()
        if not reply:
            return suggestedEmoji
        try:
            return validate_chosen_emoji(reply)
        except ValueError as error:
            print(f"  {error}")


def validate_chosen_emoji(chosenEmoji):
    """
    *check a user-supplied emoji is usable in a folder name*

    Deliberately permissive about what counts as an emoji - a user who
    wants a plain symbol should get one - but rejects the characters that
    would break or redirect folder creation.

    **Key Arguments:**

    - ``chosenEmoji`` -- the emoji supplied by the user

    **Return:**

    - ``chosenEmoji`` -- the validated emoji, stripped of surrounding whitespace
    """
    candidate = (chosenEmoji or "").strip()
    if not candidate:
        raise ValueError("an emoji is required")
    for illegal in ("/", "\\", "\n", "\r", "\0"):
        if illegal in candidate:
            raise ValueError(f"'{candidate}' cannot be used in a folder name")
    return candidate


def llm_enabled(settings):
    """
    *check whether the Claude-backed suggester is switched on in the settings*

    **Key Arguments:**

    - ``settings`` -- the aardvark settings dict, or `None`

    **Return:**

    - ``enabled`` -- `True` unless the settings explicitly disable it
    """
    emojiSettings = (settings or {}).get("emoji") or {}
    return bool(emojiSettings.get("use_llm", True))


def _validate_single_emoji(text):
    """
    *accept a model reply only if it is exactly one known emoji*

    `emoji.EMOJI_DATA` membership covers bare, variation-selector and ZWJ
    sequence spellings while rejecting anything with stray text around it,
    so it doubles as the guard against a chatty reply.

    **Key Arguments:**

    - ``text`` -- the raw reply text

    **Return:**

    - ``validated`` -- the emoji character, or `None` if the reply was not one emoji
    """
    candidate = (text or "").strip()
    return candidate if candidate in emoji.EMOJI_DATA else None


def _suggest_via_claude(title, description="", log=None):
    """
    *ask Claude for a single emoji for a folder, returning `None` on any failure*

    **Key Arguments:**

    - ``title`` -- the folder's title
    - ``description`` -- the folder's description. Default `""`.
    - ``log`` -- logger. Default `None`.

    **Return:**

    - ``suggestedEmoji`` -- the validated emoji character, or `None`
    """
    # IMPORTED LAZILY SO THE OFFLINE PATH NEVER PAYS THE IMPORT COST AND A
    # MISSING PACKAGE DEGRADES INSTEAD OF CRASHING.
    try:
        import anthropic
    except ImportError:
        if log:
            log.debug("the `anthropic` package is not installed - using the offline emoji picker")
        return None

    prompt = f"Folder title: {title}"
    if description:
        prompt += f"\nFolder description: {description}"

    try:
        client = anthropic.Anthropic(
            timeout=CLAUDE_TIMEOUT_SECONDS, max_retries=CLAUDE_MAX_RETRIES
        )
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=CLAUDE_MAX_TOKENS,
            output_config={"effort": CLAUDE_EFFORT},
            system=_SUGGESTER_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as error:
        if log:
            log.debug(f"could not reach the Claude API ({error}) - using the offline emoji picker")
        return None

    # CHECKED BEFORE READING `content`: A POLICY REFUSAL COMES BACK AS A
    # SUCCESSFUL RESPONSE WHOSE `content` MAY BE EMPTY.
    if getattr(response, "stop_reason", None) == "refusal":
        if log:
            log.debug("the Claude API declined the emoji request - using the offline emoji picker")
        return None

    replyText = ""
    for block in getattr(response, "content", None) or []:
        if getattr(block, "type", None) == "text":
            replyText = block.text
            break

    suggestedEmoji = _validate_single_emoji(replyText)
    if suggestedEmoji is None and log:
        log.debug(
            f"the Claude API reply {replyText!r} was not a single emoji - using the offline emoji picker"
        )
    return suggestedEmoji
