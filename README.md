# 🤖 Daily AI Tech News Bot

Google Gemini API、GitHub Actions、LINE Messaging API（＋任意でGmail）を組み合わせ、**毎日7:12（日本時間）にAI/IT技術ニュースと関心ニュースを要約して配信するBot**です。

---

## 💡 概要

毎日、技術系RSSと関心系RSSから記事をそれぞれ最大20件取得します。1つのRSSソースだけで取得上限に達して他のソースがまったく反映されなくなることを防ぐため、**1ソースあたりの取得件数は `取得上限 ÷ ソース数` に制限**されます（例: 上限20件・6ソースなら1ソースあたり3件）。記事はRSSに記載された順に処理し、タイトルが完全一致する記事を除外します。取得した記事をGemini APIでそれぞれ要約し、2通のメッセージとしてLINE Messaging APIでPush通知します。

GitHub Actionsのスケジュール実行を利用するため、常時稼働するサーバーは必要ありません。Gemini APIやLINE Messaging APIの利用料金・上限は各サービスの契約に従います。

---

## 🏗 システム構成

```text
[ GitHub Actions (毎日7:12 JST / 手動実行可) ]
        │
        ▼
[ main.py (Python) ]
        ├── news_fetcher.py   ──> 技術系・関心系RSS (各最大20件取得、1ソースあたり均等上限、タイトル重複を除外、取得元ラベル付与)
        │       ├── paywall_filter.py ──> 有料・会員限定の配信元／記事（isAccessibleForFree=false）を除外
        │       └── note_paywall.py ──> note.comの記事は有料記事（price>0）を除外
        ├── ai_summarizer.py  ──> Gemini API (LINE向け各5件・Gmail向け各10件の要約を生成)
        ├── stats_recorder.py ──> 取得件数・選定カテゴリを data/stats.json に記録（ダッシュボード用）
        ├── line_notifier.py  ──> LINE Messaging API (2通を1回のPush APIリクエストで送信)
        └── email_formatter.py + gmail_notifier.py ──> Gmail SMTPでHTMLメール送信（任意・未設定ならスキップ）
                                         │
                                         ▼
                          [ dashboard/index.html ] ── data/stats.json を読み込んでChart.jsで可視化
```

技術系RSSにはGoogleニュース、Zenn、Qiita、note（テクノロジー・AIタグ）を使用し、AI・IT業界の動向、開発ノウハウ、個人開発・実践事例などを収集します。関心系RSSにはLifehacker Japan、Gizmodo Japan、WIRED Japan、はてなブックマーク、note（ライフハック・ガジェットタグ）を使用し、ガジェット、ライフハック、科学、生活などの記事を収集します。各RSSには `config.py` 内で取得元ラベル（例: `Zenn`, `Lifehacker`）を付与しており、ダッシュボードの取得元別集計に利用します。

### 有料・会員限定記事の除外

全文の閲覧に有料購読やログイン（会員登録）が必要な記事は、LINE配信・Gmail配信・ダッシュボード集計の対象から除外します。サイトごとに仕組みが異なるため、次の3つを組み合わせています。

| 対象 | 判定方法 | 通信 |
| --- | --- | --- |
| 全ソース（Googleニュース含む） | 配信元ドメインが `config.py` の `PAYWALLED_DOMAINS` に含まれる記事を除外。Googleニュースの記事URLは `news.google.com` 上のJavaScript遷移のため、RSSの `<source>` 要素（配信元サイトのURL）のドメインで判定 | なし |
| `"paywall_check": "page"` を指定したソース（現在はWIRED・はてなブックマーク） | 記事ページを取得し、JSON-LDの schema.org `isAccessibleForFree` が `false` の記事（一部または全文が会員限定）を除外。マークアップのないページは無料扱い | 記事ごとに1回（1ソースあたり最大10件まで） |
| note.com | 下記の価格APIで判定 | 記事ごとに1回 |

- `PAYWALLED_DOMAINS` には、日経・WSJ・Bloombergなどの有料紙に加え、ITmedia・東洋経済など会員限定記事が混在するメディアや、有料記事のある新聞社も含めています。**会員限定でない記事も一緒に除外されますが、読めない記事を配信してしまうことを避けるための割り切りです**。不要なドメインは削除、追加したい場合は追記してください（サブドメインも対象）。
- Googleニュース経由の記事は記事ページを取得できないため、配信元ドメイン単位の判定のみです（同じ配信元でも一部の記事だけ会員限定、というケースは配信元ごと除外するか通すかの二択になります）。
- 記事ページの取得に失敗して判定できなかった場合は、記事が減りすぎないよう除外せず、警告ログのみ出力します（note.comの価格APIの失敗時は、後述のとおり除外します）。
- 除外した記事は取得件数に数えず、同じソースの次の記事で補充します。

#### note.comの有料記事フィルタ

note.comの記事は、[note.comの記事情報API](https://note.com/api/v3/notes/{記事キー})が返す `price` フィールド（`0`=無料、`0`より大きい=有料）を使って無料記事かどうかを判定し、**有料記事はLINE配信・ダッシュボード集計の対象から除外**します（`note_paywall.py`）。判定に使用するAPIはnote.com側の非公開実装のため、仕様変更やエラーの可能性があります。記事キーの取得やAPI呼び出しに失敗した場合は安全側に倒し、その記事を除外します。

Geminiへのプロンプトで、技術ニュースと関心ニュースからそれぞれ5件を選定・要約します。記事の取得処理では公開日時によるフィルタリングは行っていません。

Geminiは `gemini-3.6-flash` を優先し、失敗した場合は `gemini-3.8-flash` を使用します。各モデルへのAPI呼び出しは最大3回まで再試行します。

## 📧 Gmail通知（任意）

LINEに加えて、より件数の多い・詳しい要約をGmailで受け取ることができます。`GMAIL_ADDRESS` / `GMAIL_APP_PASSWORD` が未設定の場合、Gmail送信は自動的にスキップされ、LINE配信には一切影響しません。

- **件数**: LINEの2倍（技術系10件・関心系10件）。Gemini呼び出しがLINE用と別に発生するため、1回の実行あたりのAPI呼び出し回数は2回→4回に増えます
- **要約の形式**: 1記事あたり要点を2〜3個の箇条書きで表示。関心ニュースのうち実践的な内容の記事には「💡今日から試せること」を追加表示（記事の性質上そぐわない場合は省略）
- **形式**: HTMLメール（記事ごとにタイトルをリンク化したカード形式、1通にまとめて送信）。スマホで文字の表示幅を広く取れるよう、余白を最小限にした省スペースのレイアウトを基本とし、600px以上の広い画面でのみ余白を広げます。長いURLや英単語は折り返して、横にはみ出さないようにしています（はみ出すとGmailがメール全体を縮小表示するため）
- **送信方式**: Gmail SMTP + [アプリパスワード](https://myaccount.google.com/apppasswords)（Googleアカウントの2段階認証が前提。新しい外部サービスへの登録は不要）
- **宛先**: `GMAIL_ADDRESS` 宛（送信元・送信先は同一アドレス）
- **件名**: `🤖 [リポジトリ名] ニュース要約 - 日付` の形式（例: `🤖 [my-ai-news-bot] ニュース要約 - 2026/11/01(日)`）。Gmailのフィルタ設定で`[リポジトリ名]`を条件にラベル分け・振り分けができます。リポジトリ名はGitHub Actions実行時に自動取得され、フォークして名前を変えた場合も追従します（ローカル実行時は`my-ai-news-bot`固定）

### 設定手順

1. Googleアカウントで**2段階認証**を有効化します。
2. [Googleアプリパスワード](https://myaccount.google.com/apppasswords)で新しいアプリパスワードを発行します。
3. GitHubリポジトリの **Settings > Secrets and variables > Actions** に次のSecretsを追加します。

| Secret名 | 内容 |
| --- | --- |
| `GMAIL_ADDRESS` | Gmailアドレス（送信元・宛先として使用） |
| `GMAIL_APP_PASSWORD` | 手順2で発行したアプリパスワード |

### 注意事項

- Gmail用の要約（10件）とLINE用の要約（5件）は**別々にGeminiへ問い合わせます**。同じ記事リストから選定するため内容は近くなりますが、完全に一致するとは限りません。
- `data/stats.json`のカテゴリー集計（ダッシュボード）は**LINE用の要約（5件）のみ**を基準にしており、Gmail用の件数は含まれません。
- Geminiの出力テキストの解析に失敗した記事があっても、その記事だけ生テキスト表示にフォールバックし、メール全体の送信は継続します。

## 📊 ダッシュボード

`dashboard/index.html` は、Chart.js（CDN読み込み、追加の依存パッケージ不要）を使った静的ダッシュボードです。`data/stats.json` を取得して、以下を可視化します。

- **日々の記事数**: 技術系ニュース・関心ニュースの取得件数の推移（直近30日、積み上げ棒グラフ）
- **トピックごとのカテゴリー分け**: Geminiが要約に採用したカテゴリ（`【カテゴリ】タイトル` の表記から抽出）の件数を、日付選択式の横棒グラフで表示

各グラフには表形式への切り替えボタンがあり、グラフを使わずにも同じデータを確認できます。

### データの流れ

`main.py` の実行ごとに `stats_recorder.py` が以下を計算し、`data/stats.json` の該当日のレコードを追加・上書きします（統計データの記録に失敗してもLINE配信は継続されます）。

- `fetched`: 技術系・関心系それぞれの取得記事数と合計
- `sources`: RSS取得元ラベル別の記事数
- `selected_categories`: Geminiが要約内で選定したカテゴリ名ごとの件数

`data/stats.json` は直近90日分のみ保持し、ファイルの肥大化を防ぎます。

### GitHub Pagesでの公開（任意）

ダッシュボードをWeb上で確認したい場合は、`.github/workflows/pages.yml` を使ってGitHub Pagesに公開できます。このワークフローは **`dashboard/index.html` と `data/stats.json` のみ** をPagesの公開対象として配信し、`main.py` / `config.py` / `stats_recorder.py` などのソースコードやワークフロー定義は公開対象に含めません（リポジトリの可視性が `private` でも、Pagesサイト自体は一般公開される点に注意してください）。

1. GitHubリポジトリの **Settings > Pages** を開き、**Source** を `GitHub Actions` に設定します（`Deploy from a branch` は選ばないでください。ブランチ全体＝ソースコードも公開されてしまいます）。
2. `.github/workflows/pages.yml` が `main` ブランチにマージされていれば、`dashboard/**` または `data/stats.json` の更新時に自動でデプロイされます。初回は **Actions > Deploy Dashboard to GitHub Pages > Run workflow** から手動実行してください。

設定後、`https://<GitHubユーザー名>.github.io/my-ai-news-bot/dashboard/` でダッシュボードを閲覧できます。`daily_news.yml` が `data/stats.json` を更新するたびに `pages.yml` が連動して再デプロイされます。

### ローカルでダッシュボードを確認する

```bash
python -m http.server 8000
```

その後 `http://localhost:8000/dashboard/` をブラウザで開いてください（`data/stats.json` がまだ存在しない場合は、データ未取得である旨のメッセージが表示されます）。

## 🔑 必要な設定

GitHubリポジトリの **Settings > Secrets and variables > Actions** に、次のSecretsを登録してください。

| Secret名 | 内容 | 必須 |
| --- | --- | --- |
| `GEMINI_API_KEY` | Google AI Studioで発行したGemini APIキー | ✅ |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Messaging APIのチャネルアクセストークン | ✅ |
| `LINE_USER_ID` | 通知先ユーザーのID | ✅ |
| `GMAIL_ADDRESS` | Gmail通知を使う場合の送信元・宛先アドレス | 任意（Gmail通知を使う場合） |
| `GMAIL_APP_PASSWORD` | Gmail通知を使う場合のアプリパスワード | 任意（Gmail通知を使う場合） |

## 🚀 セットアップ

1. このリポジトリをGitHubに作成またはForkします。
2. 上記のSecretsを **Settings > Secrets and variables > Actions** に登録します（Gmail通知を使わない場合は`GMAIL_*`は不要です）。
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
# 任意: Gmail通知を使う場合のみ
export GMAIL_ADDRESS="your-gmail-address@gmail.com"
export GMAIL_APP_PASSWORD="your-gmail-app-password"
python main.py
```

### 依存ライブラリ

`requirements.txt` には次のライブラリを定義しています。バージョンは下限のみ指定しており、固定はしていません。

| ライブラリ | 用途 |
| --- | --- |
| `google-genai` | Gemini APIによる要約生成 |
| `feedparser` | RSSの解析 |
| `requests` | LINE Messaging APIへのHTTP通信、有料・会員限定記事の判定（note.com価格API、記事ページ取得） |

## ⚠️ 注意事項

- RSSの取得に失敗したURLがあっても、警告を出して他のURLの処理を続けます。
- すべてのRSSから記事を取得できなかった場合、該当する要約は「本日は対象の記事を取得できませんでした。」になります。
- 有料・会員限定の記事を除外するため、RSSの記事数より実際に要約対象となる件数が少なくなることがあります。同じソースの次の記事で補充しますが、補充できる記事がなければ件数は上限に満たないまま進みます。
- Gmail通知を有効にすると、1回の実行あたりのGemini API呼び出し回数が2回→4回に増えます（無料枠のレート制限にご注意ください）。
- Gemini APIは `gemini-3.6-flash` を最大3回試行し、失敗した場合に `gemini-3.8-flash` を最大3回試行します。各試行の間隔は5秒です。
- 処理中にエラーが発生した場合は、エラー内容をLINEへ通知しようとします。LINEへのエラー通知にも失敗した場合はログに記録します。
- RSSの重複除外は記事タイトルの完全一致で行います。URL一致や類似タイトルによる重複除外は行いません。
- APIキー、アクセストークン、ユーザーIDはソースコードに直接記載せず、環境変数またはGitHub Actions Secretsで管理してください。
---

## 📁 ディレクトリ構成

```text
my-ai-news-bot/
├── .github/
│   └── workflows/
│       ├── daily_news.yml   # GitHub Actions 実行設定（毎日7:12 JST・手動実行可、data/stats.jsonの自動コミットを含む）
│       └── pages.yml        # dashboard/とdata/stats.jsonのみをGitHub Pagesへ公開（ソースコードは非公開のまま）
├── dashboard/
│   └── index.html           # 記事数・カテゴリー分けの可視化ダッシュボード（Chart.js, CDN読み込み）
├── data/
│   └── stats.json           # 日次統計データ（直近90日分、ワークフローが自動更新）
├── config.py                # 定数・環境変数の集約、RSSソース（URL+取得元ラベル）・プロンプトの定義
├── news_fetcher.py          # RSSの取得モジュール（取得元ラベルを各記事に付与）
├── paywall_filter.py        # 有料・会員限定記事の判定モジュール（配信元ドメイン／isAccessibleForFree）
├── note_paywall.py          # note.comの有料記事判定モジュール（無料記事のみ残す）
├── ai_summarizer.py         # Gemini API連携・要約モジュール（LINE向け/Gmail向け）
├── stats_recorder.py        # ダッシュボード用の日次統計データ記録モジュール
├── line_notifier.py         # LINE Messaging API送信モジュール
├── email_formatter.py       # Gemini要約テキスト→HTMLメール変換モジュール
├── gmail_notifier.py        # Gmail SMTP送信モジュール（任意機能）
├── main.py                  # 全体を統括するメイン処理
├── requirements.txt         # 依存ライブラリ一覧
└── README.md                # プロジェクト説明
```