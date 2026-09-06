import time
import logging
from google import genai
from config import GEMINI_API_KEY, PROMPT_TECH, PROMPT_INTEREST

def generate_summary_by_prompt(articles: list[dict], prompt_template: str) -> str:
    """指定された記事リストとプロンプトでGemini要約を生成する"""
    if not articles:
        return "本日は対象の記事を取得できませんでした。"

    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY が環境変数に設定されていません。")

    news_text_list = [f"{i}. タイトル: {a['title']}\n   URL: {a['link']}" for i, a in enumerate(articles, 1)]
    formatted_news = "\n\n".join(news_text_list)
    prompt = prompt_template.format(news_content=formatted_news)

    client = genai.Client(api_key=GEMINI_API_KEY)
    candidate_models = ['gemini-3.6-flash', 'gemini-2.5-flash']

    for model_name in candidate_models:
        for attempt in range(1, 4):
            try:
                logging.info(f"モデル {model_name} で要約生成を試行中... ({attempt}/3)")
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
                if response.text:
                    return response.text
            except Exception as e:
                logging.warning(f"{model_name} 試行失敗 ({attempt}/3): {e}")
                time.sleep(5)

    raise RuntimeError("すべてのモデルでAI要約生成に失敗しました。")

def generate_both_summaries(tech_articles: list[dict], interest_articles: list[dict]) -> tuple[str, str]:
    """技術ニュースと関心ニュースの2パターンの要約を作成する"""
    logging.info("--- 技術ニュース要約作成開始 ---")
    tech_summary = generate_summary_by_prompt(tech_articles, PROMPT_TECH)
    
    logging.info("--- 関心ニュース要約作成開始 ---")
    interest_summary = generate_summary_by_prompt(interest_articles, PROMPT_INTEREST)
    
    return tech_summary, interest_summary