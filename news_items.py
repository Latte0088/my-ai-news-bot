"""Geminiの構造化出力（JSON）を検証・整形するモジュール。

Geminiが返したJSONテキストを、取得済み記事リストと突き合わせて
信頼できる記事アイテムのリストに変換する。標準ライブラリのみに依存し、
単体テストから直接 import できるようにしている。

記事アイテムの形式:
    {
        "title": str,       # 記事タイトル
        "url": str,         # 記事URL（取得済み記事の link と一致するもののみ採用）
        "source": str,      # 取得元ラベル（取得済み記事のデータを正とする）
        "category": str,    # Geminiが付けたカテゴリ名
        "summary": str,     # Geminiが自分の言葉で書いた要約
        "importance": int,  # 重要度 1〜5
    }
"""
import json
import logging
import re

# コードフェンス（```json ... ```）を取り除くためのパターン
_CODE_FENCE_PATTERN = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)

DEFAULT_IMPORTANCE = 3
MIN_IMPORTANCE = 1
MAX_IMPORTANCE = 5


def _coerce_importance(value) -> int:
    """重要度を int 化して 1〜5 に丸める。変換できない場合は既定値を使う"""
    try:
        importance = int(float(value))
    except (TypeError, ValueError):
        return DEFAULT_IMPORTANCE
    return max(MIN_IMPORTANCE, min(MAX_IMPORTANCE, importance))


def _extract_json_text(text: str) -> str:
    """コードフェンスや前後の説明文を取り除き、JSON配列らしい部分だけを取り出す"""
    stripped = _CODE_FENCE_PATTERN.sub("", text.strip())
    start = stripped.find("[")
    end = stripped.rfind("]")
    if start != -1 and end != -1 and end > start:
        return stripped[start:end + 1]
    return stripped


def parse_articles_json(text: str, fetched_articles: list[dict]) -> list[dict]:
    """GeminiのJSON出力を検証し、記事アイテムのリストに変換する。

    - URLが取得済み記事の "link" と一致しないアイテムは採用しない
      （モデルが存在しない記事を作り出すのを防ぐ）。
    - "source" は取得済み記事のデータを正とし、モデルの出力は使わない。
    - "title" が空の場合は取得済み記事のタイトルで補完する。
    - 同一URLが複数回現れた場合は最初の1件のみ採用する。
    """
    if not text:
        return []

    try:
        parsed = json.loads(_extract_json_text(text))
    except json.JSONDecodeError as e:
        logging.warning(f"Gemini出力のJSONパースに失敗しました: {e}")
        return []

    if not isinstance(parsed, list):
        logging.warning("Gemini出力がJSON配列ではありませんでした")
        return []

    fetched_by_link = {}
    for article in fetched_articles:
        link = article.get("link")
        if link and link not in fetched_by_link:
            fetched_by_link[link] = article

    items = []
    seen_urls = set()
    for raw in parsed:
        if not isinstance(raw, dict):
            continue
        url = str(raw.get("url") or "").strip()
        fetched = fetched_by_link.get(url)
        if fetched is None or url in seen_urls:
            continue
        seen_urls.add(url)

        title = str(raw.get("title") or "").strip() or str(fetched.get("title", "")).strip()
        item = {
            "title": title,
            "url": url,
            "source": str(fetched.get("source", "")),
            "category": str(raw.get("category") or "").strip(),
            "summary": str(raw.get("summary") or "").strip(),
            "importance": _coerce_importance(raw.get("importance", DEFAULT_IMPORTANCE)),
        }
        # 「今日から試せること」（任意）: 空でない場合だけ保持する
        tip = str(raw.get("tip") or "").strip()
        if tip:
            item["tip"] = tip
        items.append(item)

    return items


def filter_importance(items: list[dict], minimum: int) -> list[dict]:
    """重要度が minimum 以上のアイテムだけを返す"""
    return [item for item in items if item.get("importance", DEFAULT_IMPORTANCE) >= minimum]


def build_importance5_message(items: list[dict], date_str: str, page_url: str) -> str | None:
    """重要度5のアイテムだけを集めたLINE通知メッセージを作成する。

    重要度5のアイテムがなければ None を返す（呼び出し側は送信をスキップする）。
    """
    top_items = [item for item in items if item.get("importance") == MAX_IMPORTANCE]
    if not top_items:
        return None

    lines = [
        "🚨 重要ニュース（重要度5）",
        f"📅 {date_str}",
        "",
    ]
    for item in top_items:
        category = item.get("category", "")
        header = f"【{category}】{item['title']}" if category else item["title"]
        lines.append(header)
        if item.get("summary"):
            lines.append(item["summary"])
        lines.append(item["url"])
        lines.append("")

    if page_url:
        lines.append("📖 すべてのニュースはこちら")
        lines.append(page_url)

    return "\n".join(lines).strip()
