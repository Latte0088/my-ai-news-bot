import os

# --- 環境変数 ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_USER_ID = os.getenv("LINE_USER_ID")

# --- 1. AI/IT技術ニュース設定（ハイブリッド構成） ---
RSS_URLS_TECH = [
    # 業界動向・企業の最新ニュース（Googleニュース）
    "https://news.google.com/rss/search?q=AI&hl=ja&gl=JP&ceid=JP:ja",
    "https://news.google.com/rss/search?q=IT+技術&hl=ja&gl=JP&ceid=JP:ja",
    # 現場の実践知・個人開発・技術トレンド
    "https://zenn.dev/feed",
    "https://qiita.com/popular-items/feed"
]

# --- 2. 興味関心・ライフスタイルニュース設定（安定性の高い個別RSS） ---
RSS_URLS_INTEREST = [
    "https://www.lifehacker.jp/feed/index.xml",       # ライフハック・仕事術・日用品
    "https://www.gizmodo.jp/feed/index.xml",          # ガジェット・テクノロジー
    "https://wired.jp/feed/rss/",                     # サイエンス・ビジネス・カルチャー
    "https://b.hatena.ne.jp/hotentry/life.rss"        # ライフスタイル全般・トレンド
]

# --- プロンプト定義 ---

# メッセージ1：AI/IT技術（ハイブリッド選定・重複話題の排除）
PROMPT_TECH = """
あなたは優秀なIT・AI技術アナリストです。
提供されたニュース・記事リスト（過去24時間）から、エンジニアが読むべき「本当に価値のある5件」を厳選し要約を作成してください。

【厳選・偏り防止基準】
特定分野や特定ソースに偏らないよう、以下のバランスを徹底して選出してください。
- IT・AI業界の最新ニュース・動向（Googleニュース等）: 2件
- 開発現場の技術ノウハウ・検証記事（Zenn/Qiita等）: 2件
- 個人開発・作ってみた・実践事例（Zenn/Qiita等）: 1件

【重複・ノイズ排除ルール】
- 同一の話題・発表（例: 同じAIモデルのリリースニュースなど）が複数記事で含まれる場合は、最も内容が充実している1件のみを採用し、重複して選出しないでください。

【フォーマット】
📱 今朝のIT・AI技術ニュース厳選5選

1. 【カテゴリ】タイトル
要点: 2行程度で技術的インパクトや背景を解説
URL: 記事リンク

(5件分繰り返し)

---
💡 今日の技術一言コメント
(全体的な所感を1〜2行で)

【ニュース・記事リスト】
{news_content}
"""

# メッセージ2：個人関心ニュース（多様性重視）
PROMPT_INTEREST = """
あなたはパーソナルキュレーターです。
提供されたニュースリストから、朝の好奇心を刺激する「興味深く役に立つトピック5件」を厳選し要約を作成してください。

【厳選・偏り防止基準】
- ガジェット、ライフハック、サイエンス、趣味・生活など、特定のジャンルに偏らず満遍なく選出してください。
- 仕事や日常生活に役立つ実践的な知恵や、興味深いトレンドを優先してください。

【フォーマット】
☕ 本日の関心ニュース・トピック5選

1. 【ジャンル】タイトル
要点: 2行程度で概要と面白さを解説
URL: 記事リンク

(5件分繰り返し)

【ニュースリスト】
{news_content}
"""