"""news_store.py のユニットテスト（月別JSONのマージと保存）。"""
import json

from news_store import build_day_record, merge_day, month_key, save_daily_news


def _item(title):
    return {
        "title": title,
        "url": f"https://example.com/{title}",
        "source": "Zenn",
        "category": "AI",
        "summary": "要約",
        "importance": 3,
    }


def test_month_key():
    assert month_key("2026-11-15") == "2026-11"
    assert month_key("2027-01-03") == "2027-01"


def test_merge_day_adds_new_day():
    payload = {"month": "2026-11", "days": {}}
    record = build_day_record("2026-11-15", [_item("a")], [])
    merged = merge_day(payload, record)
    assert merged["month"] == "2026-11"
    assert list(merged["days"]) == ["2026-11-15"]
    assert merged["days"]["2026-11-15"]["tech"][0]["title"] == "a"
    # 元のペイロードは変更しない
    assert payload["days"] == {}


def test_merge_day_overwrites_same_date():
    payload = {"month": "2026-11", "days": {}}
    payload = merge_day(payload, build_day_record("2026-11-15", [_item("old")], []))
    payload = merge_day(payload, build_day_record("2026-11-15", [_item("new")], []))
    assert len(payload["days"]) == 1
    assert payload["days"]["2026-11-15"]["tech"][0]["title"] == "new"


def test_merge_day_keeps_other_days_sorted():
    payload = {"month": "2026-11", "days": {}}
    payload = merge_day(payload, build_day_record("2026-11-20", [], []))
    payload = merge_day(payload, build_day_record("2026-11-15", [], []))
    assert list(payload["days"]) == ["2026-11-15", "2026-11-20"]


def test_save_daily_news_writes_monthly_file(tmp_path):
    path = save_daily_news("2026-11-15", [_item("a")], [_item("b")], news_dir=tmp_path)
    assert path == tmp_path / "2026-11.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["month"] == "2026-11"
    day = payload["days"]["2026-11-15"]
    assert day["tech"][0]["title"] == "a"
    assert day["interest"][0]["title"] == "b"

    # 同日再実行で上書きされる
    save_daily_news("2026-11-15", [_item("a2")], [], news_dir=tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["days"]["2026-11-15"]["tech"][0]["title"] == "a2"

    # 別月は別ファイルになる
    other = save_daily_news("2026-12-01", [], [], news_dir=tmp_path)
    assert other == tmp_path / "2026-12.json"
    assert other.exists()
