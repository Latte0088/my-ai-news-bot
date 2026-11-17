"""news_fetcher の取得フローと paywall_filter / note_paywall の判定テスト。

CI（tests.yml）は pytest のみをインストールするため、feedparser / requests /
google-genai が存在しない。import を通す目的でのみ空スタブを差し込む
（ネットワークやAPI呼び出しは行わず、feedparser.parse は差し替える）。
"""
import sys
import types

for _name in ("feedparser", "requests"):
    sys.modules.setdefault(_name, types.ModuleType(_name))
if "google" not in sys.modules:
    _google = types.ModuleType("google")
    _google.genai = types.ModuleType("google.genai")
    sys.modules["google"] = _google
    sys.modules["google.genai"] = _google.genai

import news_fetcher
from news_fetcher import fetch_news_from_urls
from note_paywall import extract_note_key, is_note_url
from paywall_filter import get_host, get_publisher_host, is_paywalled_domain


class _Feed:
    def __init__(self, entries):
        self.entries = entries


def _entry(title, link, summary="", source_href=None):
    entry = {"title": title, "link": link, "summary": summary}
    if source_href:
        entry["source"] = {"href": source_href}
    return entry


def _fetch(monkeypatch, entries, sources=None, max_fetch=20):
    monkeypatch.setattr(news_fetcher.feedparser, "parse",
                        lambda url: _Feed(entries), raising=False)
    return fetch_news_from_urls(sources or [{"url": "https://example.com/rss", "source": "Test"}], max_fetch)


def test_fetch_dedupes_by_title_and_captures_description(monkeypatch):
    entries = [
        _entry("記事A", "https://example.com/a", "<p>概要<b>A</b></p>"),
        _entry("記事A", "https://example.com/a2", "重複タイトル"),
        _entry("記事B", "https://example.com/b"),
    ]
    articles = _fetch(monkeypatch, entries)
    assert [a["title"] for a in articles] == ["記事A", "記事B"]
    assert articles[0]["description"] == "概要 A"
    assert articles[0]["source"] == "Test"


def test_fetch_excludes_paywalled_domain(monkeypatch):
    entries = [
        _entry("日経の記事", "https://www.nikkei.com/article/1"),
        _entry("通常の記事", "https://example.com/ok"),
    ]
    articles = _fetch(monkeypatch, entries)
    assert [a["title"] for a in articles] == ["通常の記事"]


def test_fetch_excludes_google_news_from_paywalled_publisher(monkeypatch):
    entries = [
        _entry("Googleニュース経由の日経記事", "https://news.google.com/rss/articles/xyz",
               source_href="https://www.nikkei.com/"),
        _entry("Googleニュース経由の通常記事", "https://news.google.com/rss/articles/abc",
               source_href="https://example.jp/"),
    ]
    articles = _fetch(monkeypatch, entries)
    assert [a["title"] for a in articles] == ["Googleニュース経由の通常記事"]


def test_get_host_normalizes():
    assert get_host("https://Example.COM:8080/path") == "example.com"
    assert get_host("") == ""
    assert get_host(None) == ""


def test_get_publisher_host_uses_source_for_google_news():
    assert get_publisher_host("https://news.google.com/rss/x", "https://www.nikkei.com/") == "www.nikkei.com"
    assert get_publisher_host("https://example.com/a", "https://other.example/") == "example.com"
    assert get_publisher_host("https://news.google.com/rss/x") == "news.google.com"


def test_is_paywalled_domain_matches_subdomains():
    assert is_paywalled_domain("nikkei.com")
    assert is_paywalled_domain("xtech.nikkei.com")
    assert not is_paywalled_domain("fakenikkei.com")
    assert not is_paywalled_domain("example.com")
    assert not is_paywalled_domain("")


def test_note_url_and_key():
    assert is_note_url("https://note.com/user/n/n011cb7b981da")
    assert is_note_url("https://sub.note.com/x")
    assert not is_note_url("https://example.com/n/abc")
    assert extract_note_key("https://note.com/user/n/n011cb7b981da") == "n011cb7b981da"
    assert extract_note_key("https://note.com/user/m/m123") is None
