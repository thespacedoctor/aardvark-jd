import base64
import sys
from urllib.parse import parse_qs, urlparse

from aardvark_jd import doc_links


def _decode(url):
    """*decode a `hook://file/...` URL's `p=`/`n=` back to a (parentPath, name) pair*

    `parse_qs` already percent-decodes each value while splitting the
    query string, so what's left in `query["p"][0]`/`query["n"][0]` is the
    raw base64 text `hookmark_url` produced before its own `quote()` call.
    """
    query = parse_qs(urlparse(url).query)
    parentPath = base64.b64decode(query["p"][0]).decode("utf-8")
    name = base64.b64decode(query["n"][0]).decode("utf-8")
    return parentPath, name


def test_hookmark_url_on_darwin(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    url = doc_links.hookmark_url("/Users/dave/Dropbox/aardvark")
    assert url.startswith("hook://file/")
    parentPath, name = _decode(url)
    assert parentPath == "/Users/dave/Dropbox"
    assert name == "aardvark"


def test_hookmark_url_is_none_off_darwin(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    assert doc_links.hookmark_url("/Users/dave/Dropbox/aardvark") is None


def test_hookmark_url_round_trips_a_space_and_an_emoji(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    url = doc_links.hookmark_url("/Users/dave/Dropbox/A11 doctors🩺")
    assert " " not in url
    assert "🩺" not in url
    parentPath, name = _decode(url)
    assert parentPath == "/Users/dave/Dropbox"
    assert name == "A11 doctors🩺"


def test_hookmark_url_is_deterministic_for_the_same_path(monkeypatch):
    # craft_sync's idempotency check relies on the same folder always
    # producing the same markdown, so the placeholder id must be fixed,
    # not freshly generated per call.
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
