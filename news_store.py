"""選定されたニュース記事を月別JSONファイルに保存するモジュール。

data/news/YYYY-MM.json に以下の形式で保存する。GitHub Pagesの
ニュースページ生成（page_generator.py）の入力データになる。

    {
        "month": "2026-11",
        "days": {
            "2026-11-15": {
                "date": "2026-11-15",
                "tech": [記事アイテム, ...],
                "interest": [記事アイテム, ...]
            },
            ...
        }
    }

記事アイテムの形式は news_items.py を参照。
"""
import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

DEFAULT_NEWS_DIR = Path("data/news")


def today_jst_str() -> str:
    """日本時間（JST）の現在日付を YYYY-MM-DD 形式で返す"""
    jst = timezone(timedelta(hours=9))
    return datetime.now(jst).strftime("%Y-%m-%d")


def month_key(date_str: str) -> str:
    """日付文字列 "YYYY-MM-DD" から月キー "YYYY-MM" を返す"""
    return date_str[:7]


def build_day_record(date_str: str, tech_items: list[dict], interest_items: list[dict]) -> dict:
    """1日分のニュースレコードを作成する"""
    return {
        "date": date_str,
        "tech": list(tech_items),
        "interest": list(interest_items),
    }


def merge_day(payload: dict, day_record: dict) -> dict:
    """月別ペイロードに1日分のレコードをマージした新しい dict を返す。

    同じ日付のレコードが既にある場合は上書きする（同日再実行への対応）。
    日付は昇順に並べ替える。
    """
    days = dict(payload.get("days", {}))
    days[day_record["date"]] = day_record
    return {
        "month": month_key(day_record["date"]),
        "days": {date: days[date] for date in sorted(days)},
    }


def _load_month_payload(path: Path, month: str) -> dict:
    """既存の月別ファイルを読み込む。読めない場合は空のペイロードを返す"""
    if not path.exists():
        return {"month": month, "days": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("月別ファイルの形式が不正です")
        return payload
    except (json.JSONDecodeError, OSError, ValueError) as e:
        logging.warning(f"既存のニュースファイルの読み込みに失敗したため初期化します: {e}")
        return {"month": month, "days": {}}


def save_daily_news(
    date_str: str,
    tech_items: list[dict],
    interest_items: list[dict],
    news_dir: Path = DEFAULT_NEWS_DIR,
) -> Path:
    """1日分のニュースを月別JSONファイルへ保存し、保存先パスを返す"""
    month = month_key(date_str)
    news_dir.mkdir(parents=True, exist_ok=True)
    path = news_dir / f"{month}.json"

    payload = _load_month_payload(path, month)
    payload = merge_day(payload, build_day_record(date_str, tech_items, interest_items))

    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    logging.info(f"ニュースデータを保存しました: {path} ({date_str})")
    return path
