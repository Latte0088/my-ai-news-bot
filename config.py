import os

# --- 環境変数 ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_USER_ID = os.getenv("LINE_USER_ID")

# リポジトリ名とオーナー名を取得する。
# GitHub Actions実行時は GITHUB_REPOSITORY（"owner/repo"形式）が自動設定されるため
# そこから取得し、ローカル実行時など未設定の場合は固定値にフォールバックする。
_GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY", "")
REPO_NAME = _GITHUB_REPOSITORY.split("/")[-1] or "my-ai-news-bot"
REPO_OWNER = _GITHUB_REPOSITORY.split("/")[0] if "/" in _GITHUB_REPOSITORY else ""

# GitHub Pagesの公開URL（LINE通知に添えるリンク用）。
# オーナー名が分からないローカル実行時などは空文字列にし、リンクを付けない。
PAGES_URL = f"https://{REPO_OWNER}.github.io/{REPO_NAME}/" if REPO_OWNER else ""

# --- 有料・会員限定記事の除外設定 ---
# 全文の閲覧に有料購読・ログイン（会員登録）が必要になりやすい配信元ドメイン。
# 記事の配信元（Googleニュースは <source> 要素のドメイン、それ以外は記事URLのドメイン）が
# ここに含まれる記事は、配信・ダッシュボード集計の対象から除外する。
# サブドメインも対象（例: "nikkei.com" は "xtech.nikkei.com" にも一致）。
# 「無料記事も一緒に除外される」ことよりも「読めない記事を配信してしまう」ことの
# 影響が大きいため、会員限定記事が混在する配信元もまとめて除外している。
# 不要なものは削除、追加したい場合は追記する。
PAYWALLED_DOMAINS = {
    # 有料購読が前提の経済紙・海外メディア
    "nikkei.com", "nikkeibp.co.jp",
    "wsj.com", "bloomberg.com", "bloomberg.co.jp", "ft.com", "economist.com",
    "nytimes.com", "washingtonpost.com", "newspicks.com",
    # 会員限定記事が混在するメディア
    "itmedia.co.jp", "diamond.jp", "toyokeizai.net", "forbesjapan.com",
    "jbpress.ismedia.jp", "president.jp",
    # 有料・会員限定記事がある新聞社（Yahoo!ニュース経由の配信は対象外）
    "asahi.com", "mainichi.jp", "yomiuri.co.jp", "sankei.com",
}

# --- 1. AI/IT技術ニュース設定（ハイブリッド構成） ---
# 各RSSには "source" ラベルを付与し、ダッシュボードでの取得元別集計に使用する。
# "paywall_check": "page" を指定したソースは、記事ページを取得して
# schema.orgの isAccessibleForFree が false の記事（会員限定記事）を除外する。
# Googleニュースのリンクは news.google.com 上のJavaScript遷移のため、
# 記事ページを取得できず、配信元ドメイン（PAYWALLED_DOMAINS）による除外のみ行う。
RSS_SOURCES_TECH = [
    # 業界動向・企業の最新ニュース（Googleニュース）
    {"url": "https://news.google.com/rss/search?q=AI&hl=ja&gl=JP&ceid=JP:ja", "source": "Googleニュース(AI)"},
    {"url": "https://news.google.com/rss/search?q=IT+技術&hl=ja&gl=JP&ceid=JP:ja", "source": "Googleニュース(IT)"},
    # 現場の実践知・個人開発・技術トレンド
    {"url": "https://zenn.dev/feed", "source": "Zenn"},
    {"url": "https://qiita.com/popular-items/feed", "source": "Qiita"},
    # note（技術・AI系ハッシュタグ）
    {"url": "https://note.com/hashtag/テクノロジー/rss", "source": "note(テクノロジー)"},
    {"url": "https://note.com/hashtag/AI/rss", "source": "note(AI)"},
]

# --- 2. 興味関心・ライフスタイルニュース設定（安定性の高い個別RSS） ---
RSS_SOURCES_INTEREST = [
    {"url": "https://www.lifehacker.jp/feed/index.xml", "source": "Lifehacker"},       # ライフハック・仕事術・日用品
    {"url": "https://www.gizmodo.jp/feed/index.xml", "source": "Gizmodo"},             # ガジェット・テクノロジー
    {"url": "https://wired.jp/feed/rss/", "source": "WIRED", "paywall_check": "page"},  # サイエンス・ビジネス・カルチャー（一部会員限定記事あり）
    {"url": "https://b.hatena.ne.jp/hotentry/life.rss", "source": "はてなブックマーク", "paywall_check": "page"},  # ライフスタイル全般・トレンド（リンク先は様々なサイト）
    # note（ライフハック・ガジェット系ハッシュタグ）
    {"url": "https://note.com/hashtag/ライフハック/rss", "source": "note(ライフハック)"},
    {"url": "https://note.com/hashtag/ガジェット/rss", "source": "note(ガジェット)"},
]

# --- プロンプト定義 ---
# Geminiには構造化されたJSON配列で返させる。パースと検証は news_items.py が行う。
# プロンプト内の {date_str} / {news_content} は str.format で埋め込むため、
# JSON例に含まれる波括弧は {{ }} と二重にエスケープしている。

# 技術ニュース用（JSON出力、10件）
PROMPT_TECH_JSON = """
あなたは優秀なIT・AI技術アナリストです。
提供されたニュース・記事リスト（過去24時間）から、エンジニアが読むべき「本当に価値のある10件」を厳選し、JSON形式で出力してください。

【厳選・偏り防止基準】
- IT・AI業界の最新ニュース・動向（Googleニュース等）: 4件
- 開発現場の技術ノウハウ・検証記事（Zenn/Qiita等）: 4件
- 個人開発・作ってみた・実践事例（Zenn/Qiita/note等）: 2件

【重複・ノイズ排除ルール】
- 同一の話題・発表が複数記事で含まれる場合は、最も内容が充実している1件のみを採用してください。

【出力形式】
- 出力はJSON配列のみとしてください。説明文やコードフェンスは付けないでください。
- 各要素は次の形式のオブジェクトにしてください:
  {{"title": "記事タイトル", "url": "記事URL", "category": "カテゴリ名", "summary": "要約", "importance": 3}}
- "url" は記事リストに記載されたURLをそのまま使ってください。リストにない記事を作り出さないでください。
- "summary" は、記事の内容をあなた自身の言葉で書き直した要約にしてください。要点を2〜3個、改行で区切って1行に1要点ずつ書いてください（行頭に箇条書き記号は付けない）。1要点は60文字以内を目安に簡潔にし、技術的インパクトや背景を含めてください。記事本文の文章をそのまま転載しないでください。
- "importance" は次の基準で1〜5の整数を付けてください:
  - 5: 速報性が高く、仕事や生活に直結する重大なニュース（大型モデルのリリース、重大な脆弱性・障害、公式の重要発表など）
  - 4: 多くの読者に影響する重要な話題
  - 3: 標準的な有益情報
  - 2: 軽めの話題・ニッチな情報
  - 1: 話題程度の小さな情報

【対象日】
{date_str}

【ニュース・記事リスト】
{news_content}
"""

# 関心ニュース用（JSON出力、10件）
PROMPT_INTEREST_JSON = """
あなたはパーソナルキュレーターです。
提供されたニュースリストから、朝の好奇心を刺激する「興味深く役に立つトピック10件」を厳選し、JSON形式で出力してください。

【厳選・偏り防止基準】
- ガジェット、ライフハック、サイエンス、趣味・生活など、特定のジャンルに偏らず満遍なく選出してください。
- 仕事や日常生活に役立つ実践的な知恵や、興味深いトレンドを優先してください。

【重複・ノイズ排除ルール】
- 同一の話題が複数記事で含まれる場合は、最も内容が充実している1件のみを採用してください。

【出力形式】
- 出力はJSON配列のみとしてください。説明文やコードフェンスは付けないでください。
- 各要素は次の形式のオブジェクトにしてください:
  {{"title": "記事タイトル", "url": "記事URL", "category": "ジャンル名", "summary": "要約", "importance": 3, "tip": "今日から試せること"}}
- "url" は記事リストに記載されたURLをそのまま使ってください。リストにない記事を作り出さないでください。
- "summary" は、記事の内容をあなた自身の言葉で書き直した要約にしてください。要点を2〜3個、改行で区切って1行に1要点ずつ書いてください（行頭に箇条書き記号は付けない）。1要点は60文字以内を目安に簡潔にし、概要だけでなく面白さのポイントを含めてください。記事本文の文章をそのまま転載しないでください。
- "tip" は、実践的な内容の記事の場合に、読者が今日から試せる具体的な行動を1文で書いてください。記事の性質上そぐわない場合は "tip" のキー自体を付けないでください。
- "importance" は次の基準で1〜5の整数を付けてください:
  - 5: 速報性が高く、仕事や生活に直結する重大なニュース（生活に大きな影響のある発表、重大な障害・リコールなど）
  - 4: 多くの読者に影響する重要な話題
  - 3: 標準的な有益情報
  - 2: 軽めの話題・ニッチな情報
  - 1: 話題程度の小さな情報

【対象日】
{date_str}

【ニュースリスト】
{news_content}
"""
