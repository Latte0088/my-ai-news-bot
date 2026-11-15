"""news_items.py のユニットテスト（JSONパース・重要度フィルタ・LINE文面）。"""
import json

from news_items import (
    build_importance5_message,
    filter_importance,
    parse_articles_json,
)

FETCHED = [
    {"title": "記事Aのタイトル", "link": "https://example.com/a", "source": "Zenn"},
    {"title": "記事Bのタイトル", "link": "https://example.com/b", "source": "Qiita"},
    {"title": "記事Cのタイトル", "link": "https://example.com/c", "source": "Lifehacker"},
]


def _item(url, **overrides):
    base = {
        "title": "モデル側タイトル",
        "url": url,
        "category": "カテゴリ",
        "summary": "要約テキスト",
        "importance": 3,
    }
    base.update(overrides)
    return base


def test_parse_valid_json():
    text = json.dumps([
        _item("https://example.com/a", importance=5),
        _item("https://example.com/b", importance=2),
    ])
    items = parse_articles_json(text, FETCHED)
    assert len(items) == 2
    assert items[0]["url"] == "https://example.com/a"
    assert items[0]["importance"] == 5
    # source は取得済み記事のデータが正
    assert items[0]["source"] == "Zenn"
    assert items[1]["source"] == "Qiita"


def test_parse_fenced_json():
    text = "```json\n" + json.dumps([_item("https://example.com/a")]) + "\n```"
    items = parse_articles_json(text, FETCHED)
    assert len(items) == 1
    assert items[0]["url"] == "https://example.com/a"


def test_parse_drops_unknown_url():
    text = json.dumps([
        _item("https://example.com/a"),
        _item("https://unknown.example.com/x"),
    ])
    items = parse_articles_json(text, FETCHED)
    assert [i["url"] for i in items] == ["https://example.com/a"]


def test_parse_title_falls_back_to_fetched():
    text = json.dumps([_item("https://example.com/b", title="")])
    items = parse_articles_json(text, FETCHED)
    assert items[0]["title"] == "記事Bのタイトル"


def test_parse_importance_clamping():
    text = json.dumps([
        _item("https://example.com/a", importance=0),
        _item("https://example.com/b", importance=9),
        {"url": "https://example.com/c", "category": "x", "summary": "y"},  # importance欠落
    ])
    items = parse_articles_json(text, FETCHED)
    by_url = {i["url"]: i for i in items}
    assert by_url["https://example.com/a"]["importance"] == 1
    assert by_url["https://example.com/b"]["importance"] == 5
    assert by_url["https://example.com/c"]["importance"] == 3


def test_parse_invalid_json_returns_empty():
    assert parse_articles_json("これはJSONではありません", FETCHED) == []
    assert parse_articles_json("", FETCHED) == []


def test_filter_importance():
    items = [
        {"title": "a", "importance": 5},
        {"title": "b", "importance": 4},
        {"title": "c", "importance": 3},
    ]
    assert [i["title"] for i in filter_importance(items, 4)] == ["a", "b"]
    assert [i["title"] for i in filter_importance(items, 5)] == ["a"]


def _make_item(title, importance):
    return {
        "title": title,
        "url": f"https://example.com/{title}",
        "source": "Zenn",
        "category": "AI",
        "summary": f"{title}の要約",
        "importance": importance,
    }


def test_build_importance5_message_includes_only_5():
    items = [_make_item("重大ニュース", 5), _make_item("普通のニュース", 4), _make_item("軽い話題", 1)]
    message = build_importance5_message(items, "2026/11/15(日)", "https://owner.github.io/repo/")
    assert message is not None
    assert "重大ニュース" in message
    assert "普通のニュース" not in message
    assert "軽い話題" not in message
    assert "https://owner.github.io/repo/" in message


def test_build_importance5_message_none_when_no_5():
    items = [_make_item("普通のニュース", 4), _make_item("軽い話題", 2)]
    assert build_importance5_message(items, "2026/11/15(日)", "https://owner.github.io/repo/") is None
    assert build_importance5_message([], "2026/11/15(日)", "") is None
