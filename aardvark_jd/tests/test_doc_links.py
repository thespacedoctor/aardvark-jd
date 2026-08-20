import base64
import sys
from urllib.parse import unquote, urlparse

from aardvark_jd import doc_links


def _decode(url):
    """*decode a `hook://file/...` URL's `p=`/`n=` back to a (parentHint, name) pair*

    `p=` is base64 of a two-component path hint (not the full parent
    path), and `n=` is percent-encoded plain text (not base64) -
    matching Hookmark's own `hook://file/` links, read off the live
    Hookmark database.
    """
    query = dict(pair.split("=", 1) for pair in urlparse(url).query.split("&"))
    parentHint = base64.b64decode(query["p"]).decode("utf-8")
    name = unquote(query["n"])
    return parentHint, name


def test_hookmark_url_on_darwin(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    url = doc_links.hookmark_url("/Users/dave/Dropbox/aardvark")
    assert url.startswith("hook://file/")
    parentHint, name = _decode(url)
    assert parentHint == "dave/Dropbox"
    assert name == "aardvark"


def test_hookmark_url_matches_a_real_captured_example(monkeypatch):
    # pins the format to a verbatim example captured from the live
    # Hookmark database (/Users/Dave/Dropbox/reading), not to a
    # description of it - only the id differs, since ours is synthetic.
    monkeypatch.setattr(sys, "platform", "darwin")
    url = doc_links.hookmark_url("/Users/Dave/Dropbox/reading")
    assert url.endswith("?p=RGF2ZS9Ecm9wYm94&n=reading")


def test_hookmark_url_id_is_nine_characters(monkeypatch):
    # regression test: an 8-character id fails a length check before
    # Hookmark ever tries to resolve the link, and it rejects the whole
    # URL outright as invalid - confirmed against all 112 `hook://file/`
    # bookmarks in the live Hookmark database, every one of them 9 chars.
    monkeypatch.setattr(sys, "platform", "darwin")
    url = doc_links.hookmark_url("/Users/dave/Dropbox/aardvark")
    id_ = url.removeprefix("hook://file/").split("?", 1)[0]
    assert len(id_) == 9


def test_hookmark_url_is_none_off_darwin(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    assert doc_links.hookmark_url("/Users/dave/Dropbox/aardvark") is None


def test_hookmark_url_round_trips_a_space_and_an_emoji(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    url = doc_links.hookmark_url("/Users/dave/Dropbox/A11 doctors🩺")
    assert " " not in url
    assert "🩺" not in url
    parentHint, name = _decode(url)
    assert parentHint == "dave/Dropbox"
    assert name == "A11 doctors🩺"


def test_hookmark_url_is_deterministic_for_the_same_path(monkeypatch):
    # craft_sync's idempotency check relies on the same folder always
    # producing the same markdown, so the synthetic id must be derived
    # deterministically from the path, not freshly generated per call.
    monkeypatch.setattr(sys, "platform", "darwin")
    first = doc_links.hookmark_url("/Users/dave/Dropbox/aardvark")
    second = doc_links.hookmark_url("/Users/dave/Dropbox/aardvark")
    assert first == second


def test_link_row_markdown_with_both_links():
    markdown = doc_links.link_row_markdown("hook://file/abc?p=Lw==&n=YQ==", "https://dropbox.example/b")
    assert markdown == "[📁 Finder](hook://file/abc?p=Lw==&n=YQ==)  ·  [🔗 Dropbox](https://dropbox.example/b)"


def test_link_row_markdown_with_only_finder():
    markdown = doc_links.link_row_markdown("hook://file/abc?p=Lw==&n=YQ==", None)
    assert markdown == "[📁 Finder](hook://file/abc?p=Lw==&n=YQ==)"
    assert "Dropbox" not in markdown


def test_link_row_markdown_with_only_dropbox():
    markdown = doc_links.link_row_markdown(None, "https://dropbox.example/b")
    assert markdown == "[🔗 Dropbox](https://dropbox.example/b)"


def test_link_row_markdown_with_neither_is_none():
    assert doc_links.link_row_markdown(None, None) is None


def test_link_row_markdown_with_all_three_links():
    markdown = doc_links.link_row_markdown(
        "hook://file/abc?p=Lw==&n=YQ==", "https://dropbox.example/b", "https://app.todoist.com/app/project/1",
    )
    assert markdown == (
        "[📁 Finder](hook://file/abc?p=Lw==&n=YQ==)  ·  "
        "[🔗 Dropbox](https://dropbox.example/b)  ·  "
        "[✅ Todoist](https://app.todoist.com/app/project/1)"
    )


def test_link_row_markdown_with_only_todoist():
    markdown = doc_links.link_row_markdown(None, None, "https://app.todoist.com/app/project/1")
    assert markdown == "[✅ Todoist](https://app.todoist.com/app/project/1)"


def test_todoist_description_markdown_with_all_three_links():
    markdown = doc_links.todoist_description_markdown(
        "hook://file/abc?p=Lw==&n=YQ==", "https://dropbox.example/b", "craftdocs://open?blockId=doc-1",
    )
    assert markdown == (
        "[📁 Finder](hook://file/abc?p=Lw==&n=YQ==)  ·  "
        "[🔗 Dropbox](https://dropbox.example/b)  ·  "
        "[🗒️ Craft](craftdocs://open?blockId=doc-1)"
    )


def test_todoist_description_markdown_with_only_craft():
    markdown = doc_links.todoist_description_markdown(None, None, "craftdocs://open?blockId=doc-1")
    assert markdown == "[🗒️ Craft](craftdocs://open?blockId=doc-1)"


def test_todoist_description_markdown_with_none_is_none():
    assert doc_links.todoist_description_markdown(None, None, None) is None
