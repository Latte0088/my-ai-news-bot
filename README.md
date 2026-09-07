# 🤖 Daily AI Tech News LINE Bot

Google Gemini API、GitHub Actions、LINE Messaging APIを組み合わせ、**毎日7:12（日本時間）にAI/IT技術ニュースと関心ニュースを要約してLINEに通知するBot**です。

---

## 💡 概要

毎日、技術系RSSと関心系RSSから記事をそれぞれ最大20件取得します。記事はRSSに記載された順に処理し、タイトルが完全一致する記事を除外します。取得した記事をGemini APIでそれぞれ要約し、2通のメッセージとしてLINE Messaging APIでPush通知します。

GitHub Actionsのスケジュール実行を利用するため、常時稼働するサーバーは必要ありません。Gemini APIやLINE Messaging APIの利用料金・上限は各サービスの契約に従います。

---

## 🏗 システム構成

```text
[ GitHub Actions (毎日7:12 JST / 手動実行可) ]
        │
        ▼
[ main.py (Python) ]
        ├── news_fetcher.py  ──> 技術系・関心系RSS (各最大20件取得、タイトル重複を除外)
        ├── ai_summarizer.py ──> Gemini API (技術系・関心系の要約を生成)
        └── line_notifier.py  ──> LINE Messaging API (2通を1回のPush APIリクエストで送信)
```

技術系RSSにはGoogleニュース、Zenn、Qiitaを使用し、AI・IT業界の動向、開発ノウハウ、個人開発・実践事例などを収集します。関心系RSSにはLifehacker Japan、Gizmodo Japan、WIRED Japan、はてなブックマークを使用し、ガジェット、ライフハック、科学、生活などの記事を収集します。

Geminiへのプロンプトで、技術ニュースと関心ニュースからそれぞれ5件を選定・要約します。記事の取得処理では公開日時によるフィルタリングは行っていません。

Geminiは `gemini-3.6-flash` を優先し、失敗した場合は `gemini-2.5-flash` を使用します。各モデルへのAPI呼び出しは最大3回まで再試行します。

## 🔑 必要な設定

GitHubリポジトリの **Settings > Secrets and variables > Actions** に、次のSecretsを登録してください。

| Secret名 | 内容 |
| --- | --- |
| `GEMINI_API_KEY` | Google AI Studioで発行したGemini APIキー |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Messaging APIのチャネルアクセストークン |
| `LINE_USER_ID` | 通知先ユーザーのID |

## 🚀 セットアップ

1. このリポジトリをGitHubに作成またはForkします。
2. 上記3つのSecretsを **Settings > Secrets and variables > Actions** に登録します。
3. `main`ブランチへ変更をPushします。
4. GitHubの **Actions > Daily AI/IT News to LINE** でワークフローを確認します。

通常はGitHub Actionsのcron（`22:12 UTC`）により、毎日日本時間7:12に実行されます。動作確認は、同じ画面の **Run workflow** から手動実行できます。

### ローカルで実行する場合

Python 3.11以上を用意し、依存関係をインストールします。

```bash
pip install -r requirements.txt
```

環境変数を設定して `main.py` を実行します。

```bash
export GEMINI_API_KEY="your-gemini-api-key"
export LINE_CHANNEL_ACCESS_TOKEN="your-line-channel-access-token"
export LINE_USER_ID="your-line-user-id"
python main.py
```

### 依存ライブラリ

`requirements.txt` には次のライブラリを定義しています。バージョンは下限のみ指定しており、固定はしていません。

| ライブラリ | 用途 |
| --- | --- |
| `google-genai` | Gemini APIによる要約生成 |
| `feedparser` | RSSの解析 |
| `requests` | LINE Messaging APIへのHTTP通信 |

## ⚠️ 注意事項

- RSSの取得に失敗したURLがあっても、警告を出して他のURLの処理を続けます。
- すべてのRSSから記事を取得できなかった場合、該当する要約は「本日は対象の記事を取得できませんでした。」になります。
- Gemini APIは `gemini-3.6-flash` を最大3回試行し、失敗した場合に `gemini-2.5-flash` を最大3回試行します。各試行の間隔は5秒です。
- 処理中にエラーが発生した場合は、エラー内容をLINEへ通知しようとします。LINEへのエラー通知にも失敗した場合はログに記録します。
- RSSの重複除外は記事タイトルの完全一致で行います。URL一致や類似タイトルによる重複除外は行いません。
- APIキー、アクセストークン、ユーザーIDはソースコードに直接記載せず、環境変数またはGitHub Actions Secretsで管理してください。
---

## 📁 ディレクトリ構成

```text
my-ai-news-bot/
├── .github/
│   └── workflows/
│       └── daily_news.yml   # GitHub Actions 実行設定（毎日7:12 JST・手動実行可）
├── config.py                # 定数・環境変数の集約
├── news_fetcher.py          # GoogleニュースRSSの取得モジュール
├── ai_summarizer.py         # Gemini API連携・要約モジュール
├── line_notifier.py         # LINE Messaging API送信モジュール
├── main.py                  # 全体を統括するメイン処理
├── requirements.txt         # 依存ライブラリ一覧
└── README.md                # プロジェクト説明
```