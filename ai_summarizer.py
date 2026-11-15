"""Gemini APIでニュースを選定・要約し、構造化データ（JSON）として返すモジュール。

各記事は news_items.py の記事アイテム形式
{title, url, source, category, summary, importance} で返される。
生成されたアイテムは news_store.py で保存され、GitHub Pagesに公開される。
"""
import time
import logging
from datetime import datetime, timezone, timedelta
from google import genai
from config import (
    GEMINI_API_KEY,
    PROMPT_TECH_JSON,
    PROMPT_INTEREST_JSON,
)
from news_items import parse_articles_json


def _get_current_date_str() -> str:
    """日本時間（JST）の現在日付と曜日文字列を取得（例: "2026/09/08(火)"）"""
    jst = timezone(timedelta(hours=9))
    now = datetime.now(jst)
    weekdays = ["月", "火", "水", "木", "金", "土", "日"]
    return f"{now.strftime('%Y/%m/%d')}({weekdays[now.weekday()]})"


def get_current_date_str() -> str:
    """日本時間（JST）の現在日付と曜日文字列を取得する（公開用）。

    main.py のLINE通知メッセージの日付表示などに使用する。
    """
    return _get_current_date_str()


def _format_news_content(articles: list[dict]) -> str:
    """プロンプトに埋め込む記事リスト文字列を作成する（タイトル・URL・出典）"""
    lines = []
    for i, article in enumerate(articles, 1):
        lines.append(
            f"{i}. タイトル: {article['title']}\n"
            f"   URL: {article['link']}\n"
            f"   出典: {article.get('source', '')}"
        )
    return "\n\n".join(lines)


def _call_gemini(prompt: str) -> str:
    """Gemini APIを呼び出して応答テキストを返す。

    gemini-2.5-flashは新規ユーザー向けに提供終了（404 NOT_FOUND）しているため、
    gemini-3.6-flash を優先し、失敗した場合は gemini-3.8-flash にフォールバックする。
    各モデルへのAPI呼び出しは最大3回まで再試行する。
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY が環境変数に設定されていません。")

    client = genai.Client(api_key=GEMINI_API_KEY)
    candidate_models = ['gemini-3.6-flash', 'gemini-3.8-flash']

    for model_name in candidate_models:
        for attempt in range(1, 4):
            try:
                logging.info(f"モデル {model_name} で要約生成を試行中... ({attempt}/3)")
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
                if response.text:
                    return response.text.strip()
            except Exception as e:
                logging.warning(f"{model_name} 試行失敗 ({attempt}/3): {e}")
                time.sleep(5)

    raise RuntimeError("すべてのモデルでAI要約生成に失敗しました。")


def _generate_structured_by_prompt(articles: list[dict], prompt_template: str) -> list[dict]:
    """指定された記事リストとプロンプトでGeminiに選定・要約させ、記事アイテムを返す"""
    if not articles:
        return []

    prompt = prompt_template.format(
        date_str=_get_current_date_str(),
        news_content=_format_news_content(articles),
    )
    response_text = _call_gemini(prompt)
    items = parse_articles_json(response_text, articles)
    logging.info(f"構造化要約: {len(items)}件の記事アイテムを採用しました")
    return items


def generate_structured_summaries(
    tech_articles: list[dict],
    interest_articles: list[dict],
) -> dict[str, list[dict]]:
    """技術ニュースと関心ニュースの構造化要約を作成する。

    戻り値: {"tech": [記事アイテム...], "interest": [記事アイテム...]}
    """
    logging.info("--- 技術ニュース要約作成開始（JSON） ---")
    tech_items = _generate_structured_by_prompt(tech_articles, PROMPT_TECH_JSON)

    logging.info("--- 関心ニュース要約作成開始（JSON） ---")
    interest_items = _generate_structured_by_prompt(interest_articles, PROMPT_INTEREST_JSON)

    return {"tech": tech_items, "interest": interest_items}
