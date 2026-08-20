import sys

from aardvark_jd import doc_links


def test_finder_url_on_darwin(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    url = doc_links.finder_url("/Users/dave/Dropbox/aardvark")
    assert url.startswith("file:///Users/dave/Dropbox/aardvark")


def test_finder_url_is_none_off_darwin(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    assert doc_links.finder_url("/Users/dave/Dropbox/aardvark") is None


def test_finder_url_quotes_special_characters(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    url = doc_links.finder_url("/Users/dave/Dropbox/A11 doctors🩺")
    assert " " not in url
    assert "🩺" not in url


def test_link_row_markdown_with_both_links():
    markdown = doc_links.link_row_markdown("file:///a", "https://dropbox.example/b")
    assert markdown == "[📁 Finder](file:///a)  ·  [🔗 Dropbox](https://dropbox.example/b)"


def test_link_row_markdown_with_only_finder():
    markdown = doc_links.link_row_markdown("file:///a", None)
    assert markdown == "[📁 Finder](file:///a)"
    assert "Dropbox" not in markdown


def test_link_row_markdown_with_only_dropbox():
    markdown = doc_links.link_row_markdown(None, "https://dropbox.example/b")
    assert markdown == "[🔗 Dropbox](https://dropbox.example/b)"


def test_link_row_markdown_with_neither_is_none():
    assert doc_links.link_row_markdown(None, None) is None
