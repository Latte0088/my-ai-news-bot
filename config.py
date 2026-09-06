import os

# APIキー・認証情報（GitHub Secretsから渡す）
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
LINE_USER_ID = os.environ.get("LINE_USER_ID")

# 取得・送信設定
MAX_NEWS_COUNT = 5  # 送信するニュースの最大件数

# GoogleニュースRSSのURL（AI / IT トピック）
RSS_URLS = [
    "https://news.google.com/rss/search?q=AI+when:1d&hl=ja&gl=JP&ceid=JP:ja",
    "https://news.google.com/rss/search?q=IT+when:1d&hl=ja&gl=JP&ceid=JP:ja"
]

# Gemini プロンプト
PROMPT_TEMPLATE = """
以下の技術ニュース（AI/IT）のリストを分析し、エンジニアや技術関心層向けにLINEで読みやすい朝のニュース要約を作成してください。

【制約事項】
- 記事の中から重要度の高いものを最大4〜5件選別してください。
- 各記事について、タイトルの箇条書きと「要点（2行程度）」を記載してください。
- 各記事の末尾に、元のURLをそのまま添えてください。
- 全体の冒頭に、今日の一言総括（1〜2行）を入れてください。
- 絵文字を適度に使用し、スマホのLINE画面で見やすいフォーマットに整えてください。

【ニュースリスト】
{news_content}
"""