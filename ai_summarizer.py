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
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
    )
    return response.text