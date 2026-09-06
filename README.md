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