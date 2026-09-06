import os

# --- 環境変数 ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_USER_ID = os.getenv("LINE_USER_ID")

# --- 1. AI/IT技術ニュース設定 ---
RSS_URLS_TECH = [
    "https://news.google.com/rss/search?q=AI&hl=ja&gl=JP&ceid=JP:ja",
    "https://news.google.com/rss/search?q=IT+技術&hl=ja&gl=JP&ceid=JP:ja"
]

# --- 2. 興味関心ニュース設定（お好みでキーワード変更可能） ---
INTEREST_KEYWORDS = ["ガジェット", "ライフハック", "ビジネス", "サイエンス"]
RSS_URLS_INTEREST = [
    f"https://news.google.com/rss/search?q={kw}&hl=ja&gl=JP&ceid=JP:ja"
    for kw in INTEREST_KEYWORDS
]

# --- プロンプト定義 ---

# メッセージ1：AI/IT技術（枠固定・偏り防止）
PROMPT_TECH = """
あなたは優秀なIT・AI技術アナリストです。
提供されたニュースリスト（過去24時間）から、エンジニアが読むべき「本当に価値のある5件」を厳選し要約を作成してください。

【厳選・偏り防止基準】
特定分野（生成AIのみ等）に偏らないよう、以下のバランスを厳守して5件を選出してください。
- AI / 機械学習の最新動向: 2件
- 開発・インフラ・クラウド技術: 2件
- IT業界・セキュリティ・注目トレンド: 1件

【フォーマット】
📱 今朝のIT・AI技術ニュース厳選5選

1. 【カテゴリ】タイトル
要点: 2行程度で技術的インパクトや背景を解説
URL: 記事リンク

(5件分繰り返し)

---
💡 今日の技術一言コメント
(全体的な所感を1〜2行で)

【ニュースリスト】
{news_content}
"""

# メッセージ2：個人関心ニュース（ジャンル重複の防止）
PROMPT_INTEREST = """
あなたはパーソナルキュレーターです。
提供されたニュースリストから、好奇心を刺激する「興味深いニュース5件」を厳選し要約を作成してください。

【厳選・偏り防止基準】
- 特定のジャンル（ガジェットのみ等）に偏らないよう、提供されたリストの異なるジャンルから満遍なく選出してください。
- 専門的すぎず、朝の話題や知識の幅を広げるのに役立つ内容を優先してください。

【フォーマット】
☕ 本日の関心ニュース・トピック5選

1. 【ジャンル】タイトル
要点: 2行程度で概要と面白さを解説
URL: 記事リンク

(5件分繰り返し)

【ニュースリスト】
{news_content}
"""