"""page_generator.py のユニットテスト（描画・ハイライト・エスケープ・著作権ガード）。"""

from page_generator import render_day, render_index, render_weekly

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
    html = render_index(_day(), ["2026-11-15", "2026-11-14"])
    for title in ("重大な技術ニュース", "普通の技術ニュース", "注目の関心ニュース", "軽い関心ニュース"):
        assert title in html
        assert f"{title}の要約です" in html
    assert "2026-11-15" in html
    # 過去ニュースは日付ごとのリンク（最新日はトップ自体なので含まない）
    assert 'href="archive/2026-11-14.html"' in html
    assert 'href="archive/2026-11-15.html"' not in html


def test_summary_rendered_as_bullets():
    day = _day()
    day["tech"] = [_item("箇条書きニュース", 3, summary="要点の1つ目です\n・要点の2つ目です\n要点の3つ目です")]
    html = render_index(day, [])
    assert html.count("<li>") == 3
    assert "<li>要点の1つ目です</li>" in html
    # 行頭の箇条書き記号は除去される
    assert "<li>・要点の2つ目です</li>" not in html
    assert "<li>要点の2つ目です</li>" in html


def test_tip_box_rendered_when_present():
    day = _day()
    day["interest"] = [_item("実践ニュース", 3, tip="今日から試せる具体的な行動です")]
    html = render_index(day, [])
    assert "今日から試せること" in html
    assert "今日から試せる具体的な行動です" in html
    assert 'class="tip"' in html


def test_summary_single_line_stays_paragraph():
    html = render_index(_day(), [])
    assert "<li>" not in html


def test_article_links_open_in_new_tab():
    html = render_index(_day(), ["2026-11-15"])
    # 記事リンクは新しいタブで開く（サイト内リンクには付けない）
    assert 'target="_blank" rel="noopener noreferrer"' in html
    assert '<a href="dashboard/" target=' not in html


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


def test_render_index_no_duplicate_items():
    # 注目のニュース（重要度4以上）に載った記事が下のセクションで重複しないこと
    day = {
        "date": "2026-11-15",
        "tech": [
            _item("技術A", 5, url="https://example.com/tech-a"),
            _item("技術B", 3, url="https://example.com/tech-b"),
        ],
        "interest": [
            _item("関心A", 4, url="https://example.com/int-a"),
            _item("関心B", 2, url="https://example.com/int-b"),
        ],
    }
    html = render_index(day, [])
    for url in ("https://example.com/tech-a", "https://example.com/tech-b",
                "https://example.com/int-a", "https://example.com/int-b"):
        assert html.count(url) == 1


def test_render_index_escapes_html():
    day = _day()
    day["tech"] = [_item('<script>alert("x")</script>', 5)]
    html = render_index(day, [])
    assert '<script>alert("x")</script>' not in html
    assert "&lt;script&gt;" in html


def test_render_index_empty_state():
    html = render_index(None, [])
    assert "まだニュースがありません" in html


def test_render_weekly_collects_highlights_only():
    days = [
        ("2026-11-15", _day()),
        ("2026-11-14", {"date": "2026-11-14", "tech": [_item("前日の注目ニュース", 4)], "interest": []}),
    ]
    html = render_weekly("2026-W46", days)
    # 重要度4以上だけが集約される
    assert "重大な技術ニュース" in html
    assert "注目の関心ニュース" in html
    assert "前日の注目ニュース" in html
    assert "普通の技術ニュース" not in html
    assert "軽い関心ニュース" not in html
    # 期間ラベルと著作権ガード
    assert "2026年11月9日" in html
    assert SENTINEL not in html


def test_render_index_weekly_nav():
    html = render_index(_day(), ["2026-11-15"], weeks=[("2026-W46", "11/9〜11/15")])
    assert 'href="weekly/2026-W46.html"' in html
    assert "週まとめ" in html


def test_render_day_page():
    html = render_day("2026-11-15", _day(), "2026-11-14", None)
    assert "2026-11-15" in html
    assert "重大な技術ニュース" in html
    assert 'href="../index.html"' in html
    # 前の日へのリンクがあり、次の日（None）は出ない
    assert 'href="2026-11-14.html"' in html
    assert "→" not in html


def test_copyright_guardrail_extra_fields_not_rendered():
    # 許可フィールド以外のデータ（本文など）は生成ページに出力されない
    html = render_index(_day(), ["2026-11-15"])
    assert SENTINEL not in html

    day_html = render_day("2026-11-15", _day(), None, None)
    assert SENTINEL not in day_html
    assert "重大な技術ニュース" in day_html
