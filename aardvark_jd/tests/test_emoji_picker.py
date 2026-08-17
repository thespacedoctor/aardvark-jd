import sys
import types

import pytest

from aardvark_jd import emoji_picker


def test_known_keyword_match():
    assert emoji_picker.pick_emoji("Hospital", "") == "🏥"


def test_no_match_falls_back():
    assert emoji_picker.pick_emoji("Xyzzyqwerty", "Blahblahblah") == emoji_picker.FALLBACK_EMOJI


def test_description_used_when_title_yields_nothing():
    picked = emoji_picker.pick_emoji("Xyzzyqwerty", "Hospital visits")
    assert picked == "🏥"


def test_title_takes_precedence_over_description():
    picked = emoji_picker.pick_emoji("Hospital", "Finance and money")
    assert picked == "🏥"


def test_case_insensitivity():
    assert emoji_picker.pick_emoji("HOSPITAL") == emoji_picker.pick_emoji("hospital")


def test_index_built_once(monkeypatch):
    emoji_picker._keywordIndex = None
    emoji_picker.pick_emoji("Hospital")
    firstIndex = emoji_picker._keywordIndex
    assert firstIndex is not None
    emoji_picker.pick_emoji("Finance")
    assert emoji_picker._keywordIndex is firstIndex


# ---------------------------------------------------------------- singularise


@pytest.mark.parametrize(
    "plural, singular",
    [("Films", "Film"), ("Links", "Link"), ("Flights", "Flight"), ("Recipes", "Recipe")],
)
def test_plural_title_matches_its_singular(plural, singular):
    assert emoji_picker.pick_emoji(plural) == emoji_picker.pick_emoji(singular)


def test_singularisation_rescues_titles_that_used_to_fall_back():
    for plural in ("Films", "Links", "Flights"):
        assert emoji_picker.pick_emoji(plural) != emoji_picker.FALLBACK_EMOJI


@pytest.mark.parametrize("plural", ["Books", "Glasses"])
def test_exact_match_wins_over_singularisation(plural):
    # these plurals are emoji keywords in their own right ("books" -> 📚), so
    # they must not be singularised away to a different emoji ("book" -> 📘)
    keywordIndex = emoji_picker._get_keyword_index()
    assert emoji_picker.pick_emoji(plural) == keywordIndex[plural.lower()]


def test_singular_forms_candidates():
    assert "story" in emoji_picker._singular_forms("stories")
    assert "box" in emoji_picker._singular_forms("boxes")
    assert "film" in emoji_picker._singular_forms("films")
    # a double-s word is not naively stripped
    assert emoji_picker._singular_forms("glass") == []


# ------------------------------------------------------------------ validator


@pytest.mark.parametrize("good", ["🏥", "🗂️", "☑️", "🧑‍⚕️", "  🏥  "])
def test_validator_accepts_a_single_emoji(good):
    assert emoji_picker._validate_single_emoji(good) == good.strip()


@pytest.mark.parametrize("bad", ["", "   ", "X", "hospital", "🏥 hospital", "🏥🏥", "<thinking>🏥</thinking>", None])
def test_validator_rejects_anything_else(bad):
    assert emoji_picker._validate_single_emoji(bad) is None


# ------------------------------------------------------------- llm_enabled


def test_llm_enabled_defaults_to_true():
    assert emoji_picker.llm_enabled(None) is True
    assert emoji_picker.llm_enabled({}) is True
    assert emoji_picker.llm_enabled({"emoji": {}}) is True


def test_llm_can_be_disabled_in_settings():
    assert emoji_picker.llm_enabled({"emoji": {"use_llm": False}}) is False


def test_disabled_llm_skips_the_api_entirely(monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("the Claude API must not be called when use_llm is false")

    monkeypatch.setattr(emoji_picker, "_suggest_via_claude", boom)
    assert emoji_picker.suggest_emoji("Hospital", settings={"emoji": {"use_llm": False}}) == "🏥"


# ------------------------------------------------------- suggester fallbacks


class _FakeBlock(object):
    def __init__(self, blockType, text=""):
        self.type = blockType
        self.text = text


class _FakeResponse(object):
    def __init__(self, content, stopReason="end_turn"):
        self.content = content
        self.stop_reason = stopReason


def _install_fake_anthropic(monkeypatch, response=None, error=None, capture=None):
    """*install a fake `anthropic` module that returns ``response`` or raises ``error``*"""

    class _FakeMessages(object):
        def create(self, **kwargs):
            if capture is not None:
                capture.update(kwargs)
            if error is not None:
                raise error
            return response

    class _FakeClient(object):
        def __init__(self, **kwargs):
            if capture is not None:
                capture["_clientKwargs"] = kwargs
            self.messages = _FakeMessages()

    fakeModule = types.ModuleType("anthropic")
    fakeModule.Anthropic = _FakeClient
    monkeypatch.setitem(sys.modules, "anthropic", fakeModule)
    return fakeModule


def test_suggester_returns_the_models_emoji(monkeypatch):
    _install_fake_anthropic(monkeypatch, response=_FakeResponse([_FakeBlock("text", "🩺")]))
    assert emoji_picker.suggest_emoji("Doctors", "GP and specialists") == "🩺"


def test_suggester_skips_thinking_blocks(monkeypatch):
    # thinking is on by default on Opus 5, so a thinking block can precede the text
    _install_fake_anthropic(
        monkeypatch,
        response=_FakeResponse([_FakeBlock("thinking", ""), _FakeBlock("text", "🩺")]),
    )
    assert emoji_picker.suggest_emoji("Doctors") == "🩺"


def test_suggester_sends_the_planned_request_shape(monkeypatch):
    capture = {}
    _install_fake_anthropic(
        monkeypatch, response=_FakeResponse([_FakeBlock("text", "🩺")]), capture=capture
    )
    emoji_picker.suggest_emoji("Doctors", "GP and specialists")

    assert capture["model"] == "claude-opus-5"
    assert capture["max_tokens"] == 1024
    assert capture["output_config"] == {"effort": "low"}
    # thinking must be left at its Opus 5 default (adaptive), never disabled
    assert "thinking" not in capture
    # a short timeout so a dead network cannot hang an interactive command
    assert capture["_clientKwargs"]["timeout"] == emoji_picker.CLAUDE_TIMEOUT_SECONDS


def test_suggester_falls_back_when_anthropic_is_missing(monkeypatch):
    realImport = __builtins__["__import__"] if isinstance(__builtins__, dict) else __builtins__.__import__

    def refuseAnthropic(name, *args, **kwargs):
        if name == "anthropic":
            raise ImportError("No module named 'anthropic'")
        return realImport(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", refuseAnthropic)
    assert emoji_picker.suggest_emoji("Hospital") == "🏥"


def test_suggester_falls_back_on_a_refusal(monkeypatch):
    _install_fake_anthropic(
        monkeypatch,
        response=_FakeResponse([], stopReason="refusal"),
    )
    assert emoji_picker.suggest_emoji("Hospital") == "🏥"


def test_suggester_falls_back_on_an_api_error(monkeypatch):
    _install_fake_anthropic(monkeypatch, error=RuntimeError("no credentials configured"))
    assert emoji_picker.suggest_emoji("Hospital") == "🏥"


@pytest.mark.parametrize("badReply", ["hospital", "🏥 hospital", "", "🏥🏥"])
def test_suggester_falls_back_on_a_non_emoji_reply(monkeypatch, badReply):
    _install_fake_anthropic(monkeypatch, response=_FakeResponse([_FakeBlock("text", badReply)]))
    assert emoji_picker.suggest_emoji("Hospital") == "🏥"


def test_suggester_falls_back_when_there_is_no_text_block(monkeypatch):
    _install_fake_anthropic(monkeypatch, response=_FakeResponse([_FakeBlock("thinking", "")]))
    assert emoji_picker.suggest_emoji("Hospital") == "🏥"


def test_suggester_never_raises_on_a_malformed_response(monkeypatch):
    _install_fake_anthropic(monkeypatch, response=object())
    assert emoji_picker.suggest_emoji("Hospital") == "🏥"
