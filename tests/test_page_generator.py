"""page_generator.py のユニットテスト（描画・ハイライト・エスケープ・著作権ガード）。"""

from page_generator import render_archive, render_index

SENTINEL = "SENTINEL_BODY_TEXT_DO_NOT_RENDER"


def _item(title, importance, **overrides):
    base = {
        "title": title,
        "url": f"https://example.com/{abs(hash(title)) % 10000}",
        "source": "Zenn",
        "category": "AI",
        "summary": f"{title}の要約です",
        "importance": importance,
    }
    base.update(overrides)
    return base


def _day():
    return {
        "date": "2026-11-15",
        "tech": [
            _item("重大な技術ニュース", 5, body=SENTINEL),
            _item("普通の技術ニュース", 3),
        ],
        "interest": [
            _item("注目の関心ニュース", 4),
            _item("軽い関心ニュース", 2),
        ],
    }


def test_render_index_contains_titles_and_summaries():
    html = render_index(_day(), ["2026-11"])
    for title in ("重大な技術ニュース", "普通の技術ニュース", "注目の関心ニュース", "軽い関心ニュース"):
        assert title in html
        assert f"{title}の要約です" in html
    assert "2026-11-15" in html
    assert 'href="archive/2026-11.html"' in html


def test_render_index_highlight_section():
    html = render_index(_day(), ["2026-11"])
    start = html.index('<section id="highlight">')
    end = html.index("</section>", start)
    highlight = html[start:end]
    # 重要度4以上だけがハイライトに入る
    assert "重大な技術ニュース" in highlight
    assert "注目の関心ニュース" in highlight
    assert "普通の技術ニュース" not in highlight
    assert "軽い関心ニュース" not in highlight


def test_render_index_escapes_html():
    day = _day()
    day["tech"] = [_item('<script>alert("x")</script>', 5)]
    html = render_index(day, [])
    assert '<script>alert("x")</script>' not in html
    assert "&lt;script&gt;" in html


def test_render_index_empty_state():
    html = render_index(None, [])
    assert "まだニュースがありません" in html


def test_copyright_guardrail_extra_fields_not_rendered():
    # 許可フィールド以外のデータ（本文など）は生成ページに出力されない
    html = render_index(_day(), ["2026-11"])
    assert SENTINEL not in html

    payload = {"month": "2026-11", "days": {"2026-11-15": _day()}}
    archive_html = render_archive("2026-11", payload)
    assert SENTINEL not in archive_html
    assert "重大な技術ニュース" in archive_html
