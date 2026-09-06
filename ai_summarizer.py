import time
import logging
from google import genai
from config import GEMINI_API_KEY, PROMPT_TEMPLATE

def generate_summary(articles: list[dict]) -> str:
    if not articles:
        return "本日は取得できたニュースがありませんでした。"

    # Geminiに渡すテキスト形式に整形
    news_text_list = []
    for idx, item in enumerate(articles, 1):
        news_text_list.append(f"{idx}. タイトル: {item['title']}\n   URL: {item['link']}")
    
    formatted_news = "\n\n".join(news_text_list)
    prompt = PROMPT_TEMPLATE.format(news_content=formatted_news)

    client = genai.Client(api_key=GEMINI_API_KEY)
    
    # 試行するモデルの優先順位リスト
    candidate_models = ['gemini-3.6-flash', 'gemini-2.5-flash']
    max_retries = 3  # モデルごとの最大再試行回数
    retry_delay = 5  # リトライ時の待ち時間（秒）

    for model_name in candidate_models:
        for attempt in range(1, max_retries + 1):
            try:
                logging.info(f"モデル {model_name} で要約生成を試行中... ({attempt}/{max_retries})")
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                return response.text
            except Exception as e:
                logging.warning(f"{model_name} の呼び出しに失敗しました: {e}")
                if attempt < max_retries:
                    logging.info(f"{retry_delay}秒後に再試行します...")
                    time.sleep(retry_delay)
                else:
                    logging.error(f"モデル {model_name} での規定回数の再試行がすべて失敗しました。")

    raise RuntimeError("すべての利用可能なモデルでAPI呼び出しに失敗しました。時間をおいて再試行してください。")