"""ダッシュボード用の日次統計データを記録するモジュール。

main.py の実行結果（取得記事・Geminiが選定した記事アイテム）から、
- 日々の記事取得数（技術系／関心系、取得元別）
- Geminiが選定した記事のカテゴリの件数
を集計し、dashboard/index.html が読み込む data/stats.json に保存する。

このモジュールの失敗が配信処理を止めないよう、呼び出し側（main.py）で
例外を捕捉して警告ログのみに留めることを想定している。
"""
import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
STATS_FILE = DATA_DIR / "stats.json"

# 保持する履歴日数（ダッシュボードの表示範囲に合わせて肥大化を防ぐ）
MAX_HISTORY_DAYS = 90


def _today_jst_str() -> str:
    """日本時間（JST）の現在日付を YYYY-MM-DD 形式で返す"""
    jst = timezone(timedelta(hours=9))
    return datetime.now(jst).strftime("%Y-%m-%d")


def _count_by_source(articles: list[dict]) -> dict[str, int]:
    """記事リストを取得元（source）別に集計する"""
    counts: dict[str, int] = {}
    for article in articles:
        source = article.get("source", "unknown")
        counts[source] = counts.get(source, 0) + 1
    return counts


def _count_selected_categories(items: list[dict]) -> dict[str, int]:
    """選定された記事アイテムのカテゴリ名を集計する"""
    counts: dict[str, int] = {}
    for item in items:
        category = item.get("category") or ""
        if category:
            counts[category] = counts.get(category, 0) + 1
    return counts


def build_daily_record(
    tech_articles: list[dict],
    interest_articles: list[dict],
    tech_items: list[dict],
    interest_items: list[dict],
) -> dict:
    """1回の実行結果から、ダッシュボード用の日次統計レコードを作成する"""
    source_counts: dict[str, int] = {}
    for label, count in _count_by_source(tech_articles).items():
        source_counts[label] = source_counts.get(label, 0) + count
    for label, count in _count_by_source(interest_articles).items():
        source_counts[label] = source_counts.get(label, 0) + count

    category_counts: dict[str, int] = {}
    for label, count in _count_selected_categories(tech_items).items():
        category_counts[label] = category_counts.get(label, 0) + count
    for label, count in _count_selected_categories(interest_items).items():
        category_counts[label] = category_counts.get(label, 0) + count

    return {
        "date": _today_jst_str(),
        "fetched": {
            "tech": len(tech_articles),
            "interest": len(interest_articles),
            "total": len(tech_articles) + len(interest_articles),
        },
        "sources": source_counts,
        "selected_categories": category_counts,
    }


def _load_existing_payload() -> dict:
    if not STATS_FILE.exists():
        return {"daily": []}
    try:
        return json.loads(STATS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logging.warning(f"既存の統計ファイルの読み込みに失敗したため初期化します: {e}")
        return {"daily": []}


def save_daily_record(record: dict) -> None:
    """統計レコードをdata/stats.jsonへ保存する（同日分がある場合は上書き）"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    payload = _load_existing_payload()
    daily = [d for d in payload.get("daily", []) if d.get("date") != record["date"]]
    daily.append(record)
    daily.sort(key=lambda d: d["date"])

    # 直近 MAX_HISTORY_DAYS 日分のみ保持し、ファイルの肥大化を防ぐ
    if len(daily) > MAX_HISTORY_DAYS:
        daily = daily[-MAX_HISTORY_DAYS:]

    payload["daily"] = daily
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()

    STATS_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    logging.info(f"統計データを更新しました: {STATS_FILE} ({record['date']})")


def record_run_stats(
    tech_articles: list[dict],
    interest_articles: list[dict],
    tech_items: list[dict],
    interest_items: list[dict],
) -> None:
    """統計レコードの作成と保存をまとめて行う"""
    record = build_daily_record(tech_articles, interest_articles, tech_items, interest_items)
    save_daily_record(record)
