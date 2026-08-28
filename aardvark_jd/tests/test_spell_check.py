import logging

import pytest

from aardvark_jd import spell_check, vocabulary

log = logging.getLogger("test_spell_check")
log.addHandler(logging.NullHandler())


@pytest.fixture
def interactive(monkeypatch):
    """*pretend stdin is a terminal, and script the answers to the prompts*"""
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)

    def scripted(answers):
        replies = list(answers)
        prompts = []

        def fakeInput(prompt=""):
            prompts.append(prompt)
            return replies.pop(0) if replies else ""

        monkeypatch.setattr("builtins.input", fakeInput)
        return prompts

    return scripted


@pytest.fixture
def nonInteractive(monkeypatch):
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)


# ---------------------------------------------------------------- the wordlist

def test_the_shipped_wordlist_is_british_english():
    """*the whole point of `en_GB-ise` - `colour` is a word, `color` is not*"""
    words = spell_check._load_words()

    assert "colour" in words and "organise" in words
    assert "color" not in words and "organize" not in words


def test_the_live_typo_this_feature_exists_for_is_caught():
    """*`aadvark` is a real typo in the user's own tree*"""
    assert spell_check.suggest("aadvark") == "aardvark"


def test_a_correctly_spelled_word_gets_no_suggestion():
    assert spell_check.suggest("cardiologist") is None
    assert spell_check.suggest("aardvark") is None


def test_a_word_two_edits_out_gets_no_suggestion():
    """*distance 2 was measured and rejected - 49 per cent false positives*"""
    assert spell_check.suggest("crdilgist") is None


# ---------------------------------------------------------------- tokenising

def test_tokens_are_split_on_separators_and_short_ones_ignored():
    """*short tokens are where the false positives live*"""
    assert spell_check.tokenise("Aadvark_notes-and.things xyz") == ["Aadvark", "things"]


def test_tokens_below_the_minimum_length_are_never_checked():
    assert spell_check.tokenise("teh cat sat") == []


def test_non_alphabetic_tokens_are_skipped():
    assert spell_check.tokenise("A11.10 project2024 hello1") == []


# ---------------------------------------------------------------- the prompt

def test_accepting_a_correction_rewrites_only_that_token(interactive, tmp_path):
    interactive(["y"])

    corrected = spell_check.check_title("Aadvark notes", rootPath=str(tmp_path), log=log)

    assert corrected == "Aardvark notes"


def test_an_accepted_correction_keeps_the_original_capitalisation(interactive, tmp_path):
    interactive(["y"])
    assert spell_check.check_title("Aadvark", rootPath=str(tmp_path), log=log) == "Aardvark"

    interactive(["y"])
    assert spell_check.check_title("aadvark", rootPath=str(tmp_path), log=log) == "aardvark"


def test_separators_and_other_tokens_survive_a_correction(interactive, tmp_path):
    interactive(["y"])

    corrected = spell_check.check_title("my_aadvark-notes.here", rootPath=str(tmp_path), log=log)

    assert corrected == "my_aardvark-notes.here"


def test_declining_keeps_the_title_exactly_as_typed(interactive, tmp_path):
    interactive(["n"])

    assert spell_check.check_title("Aadvark notes", rootPath=str(tmp_path), log=log) == "Aadvark notes"


def test_a_bare_enter_declines(interactive, tmp_path):
    interactive([""])

    assert spell_check.check_title("Aadvark", rootPath=str(tmp_path), log=log) == "Aadvark"


def test_each_suspect_token_is_prompted_separately_in_title_order(interactive, tmp_path):
    prompts = interactive(["n", "n"])

    spell_check.check_title("aadvark pydantic", rootPath=str(tmp_path), log=log)

    assert len(prompts) == 2
    assert "aadvark" in prompts[0]
    assert "pydantic" in prompts[1]


# ---------------------------------------------------------------- learning

def test_declining_teaches_it_the_word_permanently(interactive, tmp_path):
    """*the low-friction answer is the permanent one - this is why the feature self-silences*"""
    interactive(["n"])
    spell_check.check_title("pydantic models", rootPath=str(tmp_path), log=log)

    assert "pydantic" in vocabulary.load(str(tmp_path))


def test_a_learned_word_is_never_offered_again(interactive, tmp_path):
    interactive(["n"])
    spell_check.check_title("pydantic models", rootPath=str(tmp_path), log=log)

    prompts = interactive([])
    spell_check.check_title("pydantic again", rootPath=str(tmp_path), log=log)

    assert prompts == []


def test_accepting_a_correction_does_not_teach_it_the_word(interactive, tmp_path):
    interactive(["y"])

    spell_check.check_title("Aadvark", rootPath=str(tmp_path), log=log)

    assert vocabulary.load(str(tmp_path)) == frozenset()


def test_without_a_root_path_nothing_is_learned(interactive):
    """*no system root, no vocabulary - but the prompt still works*"""
    interactive(["n"])

    assert spell_check.check_title("Aadvark") == "Aadvark"


# ---------------------------------------------------------------- non-TTY

def test_a_non_interactive_run_creates_the_entity_as_typed(nonInteractive, tmp_path, capsys):
    corrected = spell_check.check_title("Aadvark notes", rootPath=str(tmp_path), log=log)

    assert corrected == "Aadvark notes"
    assert "may be a typo of 'aardvark'" in capsys.readouterr().err


def test_a_non_interactive_run_never_blocks_or_prompts(nonInteractive, tmp_path, monkeypatch):
    def mustNotPrompt(prompt=""):
        raise AssertionError("a non-interactive run must never prompt")

    monkeypatch.setattr("builtins.input", mustNotPrompt)

    spell_check.check_title("Aadvark notes", rootPath=str(tmp_path), log=log)


def test_the_non_interactive_note_is_filtered_through_the_learned_vocabulary(
    nonInteractive, tmp_path, capsys,
):
    """*a token dismissed interactively stays quiet in later scripted runs*"""
    vocabulary.remember(str(tmp_path), "aadvark", log=log)

    spell_check.check_title("Aadvark notes", rootPath=str(tmp_path), log=log)

    assert capsys.readouterr().err == ""


# ---------------------------------------------------------------- the toggle

def test_the_feature_can_be_switched_off(interactive, tmp_path, monkeypatch):
    def mustNotPrompt(prompt=""):
        raise AssertionError("spell check is disabled")

    monkeypatch.setattr("builtins.input", mustNotPrompt)
    settings = {"spell_check": {"enabled": False}}

    assert spell_check.check_title("Aadvark", rootPath=str(tmp_path), settings=settings) == "Aadvark"


def test_the_feature_is_on_by_default():
    assert spell_check.enabled(None) is True
    assert spell_check.enabled({}) is True
    assert spell_check.enabled({"spell_check": {}}) is True
    assert spell_check.enabled({"spell_check": {"enabled": True}}) is True


def test_an_empty_title_is_returned_untouched():
    assert spell_check.check_title("") == ""
    assert spell_check.check_title(None) is None


# ---------------------------------------------------------------- degradation

def test_a_missing_wordlist_disables_the_check_rather_than_breaking_it(
    monkeypatch, interactive, tmp_path,
):
    monkeypatch.setattr(spell_check, "_words", None)
    monkeypatch.setattr(spell_check, "_WORDLIST_PATH", "/no/such/wordlist.txt")

    def mustNotPrompt(prompt=""):
        raise AssertionError("with no wordlist there is nothing to suggest")

    monkeypatch.setattr("builtins.input", mustNotPrompt)
    try:
        assert spell_check.check_title("Aadvark", rootPath=str(tmp_path)) == "Aadvark"
    finally:
        spell_check._words = None


# ---------------------------------------------------------------- repeats and interrupts

def test_a_token_repeated_in_one_title_is_asked_about_once(interactive, tmp_path):
    """*one decision covers every occurrence - asking twice about the same word would be absurd*"""
    prompts = interactive(["y"])

    corrected = spell_check.check_title("aadvark and aadvark", rootPath=str(tmp_path), log=log)

    assert len(prompts) == 1
    assert corrected == "aardvark and aardvark"


def test_declining_a_repeated_token_asks_once_and_learns_once(interactive, tmp_path):
    prompts = interactive(["n"])

    corrected = spell_check.check_title("aadvark and aadvark", rootPath=str(tmp_path), log=log)

    assert len(prompts) == 1
    assert corrected == "aadvark and aadvark"
    assert "aadvark" in vocabulary.load(str(tmp_path))


def test_a_repeated_token_is_noted_once_in_a_non_interactive_run(nonInteractive, tmp_path, capsys):
    spell_check.check_title("aadvark and aadvark", rootPath=str(tmp_path), log=log)

    assert capsys.readouterr().err.count("may be a typo") == 1


def test_ctrl_d_at_the_prompt_declines_without_breaking_the_command(monkeypatch, tmp_path):
    """*this helper promises it cannot break the command, so end-of-input is a decline*"""
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)

    def endOfInput(prompt=""):
        raise EOFError()

    monkeypatch.setattr("builtins.input", endOfInput)

    assert spell_check.check_title("Aadvark notes", rootPath=str(tmp_path), log=log) == "Aadvark notes"
    # NOT A DELIBERATE DISMISSAL, SO IT TEACHES NOTHING.
    assert vocabulary.load(str(tmp_path)) == frozenset()


def test_ctrl_d_abandons_the_remaining_prompts(monkeypatch, tmp_path):
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    calls = []

    def endOfInput(prompt=""):
        calls.append(prompt)
        raise EOFError()

    monkeypatch.setattr("builtins.input", endOfInput)
    spell_check.check_title("aadvark pydantic", rootPath=str(tmp_path), log=log)

    assert len(calls) == 1


def test_a_non_dict_or_falsey_toggle_value_switches_it_off(monkeypatch, tmp_path):
    """*`enabled: 0` in YAML must disable it, not just a literal `false`*"""
    def mustNotPrompt(prompt=""):
        raise AssertionError("spell check is disabled")

    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("builtins.input", mustNotPrompt)

    assert spell_check.enabled({"spell_check": {"enabled": 0}}) is False
    assert spell_check.check_title(
        "Aadvark", rootPath=str(tmp_path), settings={"spell_check": {"enabled": 0}},
    ) == "Aadvark"


def test_checked_title_finds_the_root_path_from_settings(interactive, tmp_path):
    """*the one place the four add_* commands share, so the lookup lives in one place*"""
    interactive(["n"])
    settings = {"system": {"root_path": str(tmp_path)}}

    assert spell_check.checked_title("Aadvark", settings, log) == "Aadvark"
    assert "aadvark" in vocabulary.load(str(tmp_path))


def test_checked_title_copes_with_no_settings_at_all(interactive):
    interactive(["n"])
    assert spell_check.checked_title("Aadvark", None, log) == "Aadvark"
