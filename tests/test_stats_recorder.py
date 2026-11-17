"""stats_recorder の集計ロジックのテスト（ダッシュボード用日次統計）。"""
import re

from stats_recorder import _count_by_source, _count_selected_categories, build_daily_record


def test_count_by_source():
    articles = [{"source": "Zenn"}, {"source": "Zenn"}, {"source": "Qiita"}, {}]
    assert _count_by_source(articles) == {"Zenn": 2, "Qiita": 1, "unknown": 1}
    assert _count_by_source([]) == {}


def test_count_selected_categories_skips_empty():
    items = [{"category": "AI"}, {"category": "AI"}, {"category": ""}, {}]
    assert _count_selected_categories(items) == {"AI": 2}


def test_build_daily_record_merges_tech_and_interest():
    record = build_daily_record(
        tech_articles=[{"source": "Zenn"}, {"source": "Qiita"}],
        interest_articles=[{"source": "Zenn"}],
        tech_items=[{"category": "AI"}, {"category": "AI"}],
        interest_items=[{"category": "ガジェット"}],
    )
    assert record["fetched"] == {"tech": 2, "interest": 1, "total": 3}
    assert record["sources"] == {"Zenn": 2, "Qiita": 1}
    assert record["selected_categories"] == {"AI": 2, "ガジェット": 1}
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", record["date"])
