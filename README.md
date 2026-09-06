# 🤖 Daily AI Tech News Line Bot

Google Gemini API、GitHub Actions、LINE Messaging APIを組み合わせ、**毎朝7時にAI/IT技術ニュースと関心ニュースを要約してLINEに通知するBot**です。

---

## 💡 概要

毎朝、GoogleニュースのRSSから、AI/IT技術ニュースを最大20件、関心ニュースを最大20件取得します。取得した記事をGemini APIでそれぞれ要約し、2通のメッセージとしてLINE Messaging APIでPush通知します。

GitHub Actionsのスケジュール実行を利用するため、常時稼働するサーバーは必要ありません。Gemini APIやLINE Messaging APIの利用料金・上限は各サービスの契約に従います。

---

## 🏗 システム構成

```text
[ GitHub Actions (毎朝7:00 JST / 手動実行可) ]
        │
        ▼
[ main.py (Python) ]
        ├── news_fetcher.py  ──> Google News RSS (技術系・関心系を各最大20件取得)
        ├── ai_summarizer.py ──> Gemini API (2種類の要約を生成)
        └── line_notifier.py  ──> LINE Messaging API (2通をまとめて送信)
```

技術ニュースはAI・機械学習、開発・インフラ・クラウド、IT業界・セキュリティなどのバランスを考慮して5件に厳選します。関心ニュースも異なるジャンルから5件に厳選します。

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
2. 上記3つのSecretsを登録します。
3. `main`ブランチへ変更をPushします。
4. GitHubの **Actions > Daily AI/IT News to LINE** でワークフローを有効化します。

通常は毎日日本時間7:00に実行されます。動作確認は、同じ画面の **Run workflow** から手動実行できます。

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

処理中にエラーが発生した場合は、エラー内容をLINEへ通知しようとします。
---

## 📁 ディレクトリ構成

```text
my-ai-news-bot/
├── .github/
│   └── workflows/
│       └── daily_news.yml   # GitHub Actions 実行設定（毎朝7時・手動実行可）
├── config.py                # 定数・環境変数の集約
├── news_fetcher.py          # GoogleニュースRSSの取得モジュール
├── ai_summarizer.py         # Gemini API連携・要約モジュール
├── line_notifier.py         # LINE Messaging API送信モジュール
├── main.py                  # 全体を統括するメイン処理
├── requirements.txt         # 依存ライブラリ一覧
└── README.md                # プロジェクト説明
```