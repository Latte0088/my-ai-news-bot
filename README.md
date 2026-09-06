# 🤖 Daily AI Tech News Line Bot

Google Gemini API、GitHub Actions、LINE Messaging APIを組み合わせた、**毎朝7時に自動で最新のAI/IT技術ニュースを要約してLINEに通知するBot** です。

---

## 💡 概要

毎朝、Googleニュース（AI/ITトピック）のRSSから最新記事を取得し、Gemini API（`gemini-2.5-flash`）でエンジニア向けに要約を作成してLINEへPush通知します。
GitHub Actions上でCron実行するため、サーバーの維持費不要（完全無料）で動作します。

---

## 🏗 システム構成

```text
[ GitHub Actions (毎朝7:00 JST) ]
        │
        ▼
[ main.py (Python) ]
   ├── 1. news_fetcher.py  ──> Google News RSS (AI/IT記事を取得)
   ├── 2. ai_summarizer.py ──> Gemini API (記事を分析・要約生成)
   └── 3. line_notifier.py  ──> LINE Messaging API (スマホへPush送信)
---

## 📁 ディレクトリ構成

```text
my-ai-news-bot/
├── .github/
│   └── workflows/
│       └── daily_news.yml   # GitHub Actions 実行設定（毎朝7時）
├── config.py                # 定数・環境変数の集約
├── news_fetcher.py          # GoogleニュースRSSの取得モジュール
├── ai_summarizer.py         # Gemini API連携・要約モジュール
├── line_notifier.py         # LINE Messaging API送信モジュール
├── main.py                  # 全体を統括するメイン処理
├── requirements.txt         # 依存ライブラリ一覧
└── README.md                # プロジェクト説明
```