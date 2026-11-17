# 🤖 Daily AI Tech News Bot

Google Gemini API、GitHub Actions、LINE Messaging APIを組み合わせ、**毎朝、AI/IT技術ニュースと関心ニュースを収集・要約してGitHub Pages向けに公開し、重要度の高いニュースだけをLINEに通知するBot**です。

---

## 💡 概要

毎日、技術系RSSと関心系RSSから記事をそれぞれ最大20件取得します。1つのRSSソースだけで取得上限に達して他のソースがまったく反映されなくなることを防ぐため、**1ソースあたりの取得件数は `取得上限 ÷ ソース数` に制限**されます（例: 上限20件・6ソースなら1ソースあたり3件）。記事はRSSに記載された順に処理し、タイトルが完全一致する記事を除外します。

取得した記事はGemini APIが選定・要約し、記事ごとに `{title, url, source, category, summary, importance（重要度1〜5）}` の**構造化JSON**として生成します。選定結果は `data/news/YYYY-MM.json` に月別で保存され、GitHub Pagesのビルド時にニュースページ（トップ＋日別アーカイブ）が生成されます。LINEへは、**重要度5のニュースがある日だけ**、その一覧とページへのリンクを通知します（重要度5がない日は通知しません）。

実行はGitHub Actionsの `workflow_dispatch` で、運用では外部スケジューラ（cron-job.org）から毎朝起動しています（GitHub Actions標準のcronは使っていません）。常時稼働するサーバーは必要ありません。Gemini APIやLINE Messaging APIの利用料金・上限は各サービスの契約に従います。

> 2026年11月に、LINE／メールへのプッシュ配信中心の構成から、GitHub Pagesへのプル型公開＋重要度5のみLINE通知の構成へ移行しました。Gmailの詳細メールは廃止しています（旧 `gmail_notifier.py` / `email_formatter.py` は削除済み）。

---

## 🏗 システム構成

```text
[ cron-job.org ] ── workflow_dispatch ──> [ GitHub Actions: daily_news.yml ]
                                                    │
                                                    ▼
[ main.py (Python) ]
        ├── news_fetcher.py   ──> 技術系・関心系RSS (各最大20件取得、1ソースあたり均等上限、タイトル重複を除外、取得元ラベル付与)
        │       ├── paywall_filter.py ──> 有料・会員限定の配信元／記事（isAccessibleForFree=false）を除外
        │       └── note_paywall.py ──> note.comの記事は有料記事（price>0）を除外
        ├── ai_summarizer.py  ──> Gemini API (構造化JSONで各10件を選定・要約、重要度1〜5付き)
        │       └── news_items.py ──> Gemini出力JSONのパース・検証（取得済み記事のURLと突合、不正な項目は破棄）
        ├── news_store.py     ──> 選定結果を data/news/YYYY-MM.json に月別保存
        ├── stats_recorder.py ──> 取得件数・選定カテゴリを data/stats.json に記録（ダッシュボード用）
        └── line_notifier.py  ──> LINE Messaging API (重要度5がある日だけ通知。エラー時もLINEへ通知)

[ GitHub Actions: pages.yml ]
        ├── page_generator.py ──> data/news/ の月別JSONからニュースページ（トップ＋日別アーカイブ＋週まとめ）を生成
        └── dashboard/index.html ＋ data/stats.json をあわせてGitHub Pagesへデプロイ
```

技術系RSSにはGoogleニュース、Zenn、Qiita、note（テクノロジー・AIタグ）を使用し、AI・IT業界の動向、開発ノウハウ、個人開発・実践事例などを収集します。関心系RSSにはLifehacker Japan、Gizmodo Japan、WIRED Japan、はてなブックマーク、note（ライフハック・ガジェットタグ）を使用し、ガジェット、ライフハック、科学、生活などの記事を収集します。各RSSには `config.py` 内で取得元ラベル（例: `Zenn`, `Lifehacker`）を付与しており、ダッシュボードの取得元別集計に利用します。

### 選定と重要度

Geminiへのプロンプトで、技術ニュース10件（業界動向4件・技術ノウハウ4件・個人開発/実践2件）と関心ニュース10件を選定します。各記事には重要度1〜5が付きます（5=速報性が高く仕事・生活に直結する重大ニュース、4=重要、3=標準、2=軽め、1=話題程度）。要約はAIが自分の言葉で書いた要点3〜5個の箇条書きで、記事の紹介文ではなく中身と結論まで書きます（ページ上では折り畳み表示のため長さの制限は設けていません）。要約の材料はタイトルとRSSの概要文で、記事本文の転載はしません。関心ニュースでは、実践的な記事に「💡今日から試せること」（AIが考える具体的な行動）が付く場合があります。記事の取得処理では公開日時によるフィルタリングは行っていません。

Geminiは `gemini-3.6-flash` を優先し、失敗した場合は `gemini-3.8-flash` を使用します。各モデルへのAPI呼び出しは最大3回まで再試行します。Geminiの出力は `news_items.py` で検証し、取得した記事のURLと一致しない項目や形式が不正な項目は破棄します。

### 有料・会員限定記事の除外

全文の閲覧に有料購読やログイン（会員登録）が必要な記事は、選定対象から除外します。サイトごとに仕組みが異なるため、次の3つを組み合わせています。

| 対象 | 判定方法 | 通信 |
| --- | --- | --- |
| 全ソース（Googleニュース含む） | 配信元ドメインが `config.py` の `PAYWALLED_DOMAINS` に含まれる記事を除外。Googleニュースの記事URLは `news.google.com` 上のJavaScript遷移のため、RSSの `<source>` 要素（配信元サイトのURL）のドメインで判定 | なし |
| `"paywall_check": "page"` を指定したソース（現在はWIRED・はてなブックマーク） | 記事ページを取得し、JSON-LDの schema.org `isAccessibleForFree` が `false` の記事（一部または全文が会員限定）を除外。マークアップのないページは無料扱い | 記事ごとに1回（1ソースあたり最大10件まで） |
| note.com | 下記の価格APIで判定 | 記事ごとに1回 |

- `PAYWALLED_DOMAINS` には、日経・WSJ・Bloombergなどの有料紙に加え、ITmedia・東洋経済など会員限定記事が混在するメディアや、有料記事のある新聞社も含めています。**会員限定でない記事も一緒に除外されますが、読めない記事を取り上げてしまうことを避けるための割り切りです**。不要なドメインは削除、追加したい場合は追記してください（サブドメインも対象）。
- Googleニュース経由の記事は記事ページを取得できないため、配信元ドメイン単位の判定のみです（同じ配信元でも一部の記事だけ会員限定、というケースは配信元ごと除外するか通すかの二択になります）。
- 記事ページの取得に失敗して判定できなかった場合は、記事が減りすぎないよう除外せず、警告ログのみ出力します（note.comの価格APIの失敗時は、後述のとおり除外します）。
- 除外した記事は取得件数に数えず、同じソースの次の記事で補充します。

#### note.comの有料記事フィルタ

note.comの記事は、[note.comの記事情報API](https://note.com/api/v3/notes/{記事キー})が返す `price` フィールド（`0`=無料、`0`より大きい=有料）を使って無料記事かどうかを判定し、**有料記事は選定対象から除外**します（`note_paywall.py`）。判定に使用するAPIはnote.com側の非公開実装のため、仕様変更やエラーの可能性があります。記事キーの取得やAPI呼び出しに失敗した場合は安全側に倒し、その記事を除外します。

## 📰 ニュースページ（GitHub Pages）

`page_generator.py` が `data/news/` の月別JSONから、以下のページを生成します。

- **トップページ**: 最新日のニュース。重要度4以上を上部にハイライトし、技術・関心のセクションごとに表示。要約は開閉式（`<details>`）で掲載
- **日別アーカイブ**: `archive/YYYY-MM-DD.html` に、その日のニュース一覧をトップと同じ形式で掲載。トップページ上部の「過去のニュース」から日付ごとにリンクされ、各日ページには前日・翌日へのリンクもあります
- **週まとめ**: `weekly/YYYY-Www.html` に、その週（月〜日）の重要度4以上のニュースを日付ごとに集約。トップページ上部の「週まとめ」からリンクされます（重要度4以上が1件もない週は生成されません）

ページに掲載するのはタイトル・URL・出典・カテゴリ・要約・重要度と「今日から試せること」のみで、記事本文は転載しません。

> **現在の状態**: このリポジトリは非公開で、GitHub Pagesはまだ有効化していません（無料プランでは非公開リポジトリのPagesを公開できないため）。公開は、リポジトリの公開設定への切り替えとセットで別途行います。有効化後は、`daily_news.yml` の最終ステップから `pages.yml` を連鎖起動し、毎朝の実行に続けて自動デプロイされる構成にする予定です（外部スケジューラのジョブは従来どおり1つのまま）。

## 📊 ダッシュボード

`dashboard/index.html` は、Chart.js（CDN読み込み、追加の依存パッケージ不要）を使った静的ダッシュボードです。`data/stats.json` を取得して、以下を可視化します。

- **日々の記事数**: 技術系ニュース・関心ニュースの取得件数の推移（直近30日、積み上げ棒グラフ）
- **トピックごとのカテゴリー分け**: Geminiが選定した記事のカテゴリ（構造化JSONの `category`）の件数を、日付選択式の横棒グラフで表示

各グラフには表形式への切り替えボタンがあり、グラフを使わずにも同じデータを確認できます。ダッシュボードはニュースページと同じ `pages.yml` のビルドで、サイト内の `dashboard/` に配置されます。

### データの流れ

`main.py` の実行ごとに `stats_recorder.py` が以下を計算し、`data/stats.json` の該当日のレコードを追加・上書きします（統計データの記録に失敗しても、ニュース保存とLINE通知は継続されます）。

- `fetched`: 技術系・関心系それぞれの取得記事数と合計
- `sources`: RSS取得元ラベル別の記事数
- `selected_categories`: Geminiが選定した記事のカテゴリ名ごとの件数

`data/stats.json` は直近90日分のみ保持し、ファイルの肥大化を防ぎます。

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

## 🚀 セットアップ

1. このリポジトリをGitHubに作成またはForkします。
2. 上記のSecretsを **Settings > Secrets and variables > Actions** に登録します。
3. `main`ブランチへ変更をPushします。
4. GitHubの **Actions > Daily AI/IT News to LINE** でワークフローを確認します。

運用では、外部スケジューラ（cron-job.org）から毎朝 `workflow_dispatch` で起動しています。GitHub Actions標準のcronは精度・確実性の問題があるため使っていません。動作確認は、Actions画面の **Run workflow** から手動実行できます。

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
| `google-genai` | Gemini APIによる選定・要約生成 |
| `feedparser` | RSSの解析 |
| `requests` | LINE Messaging APIへのHTTP通信、有料・会員限定記事の判定（note.com価格API、記事ページ取得） |

## 🧪 テスト

`tests/` にpytestのテストスイートがあります（`.github/workflows/tests.yml` で、Pull Requestと `main` へのpush時に自動実行）。

- リポジトリ全体の機密情報スキャン（APIキー等のパターン検出）
- `news_items.py`: Gemini出力JSONのパース、未知URLの破棄、重要度のクランプ、重要度5メッセージ生成
- `news_store.py`: 月別JSONへのマージ・同日上書き
- `page_generator.py`: ページ生成、重要度ハイライト、HTMLエスケープ、余分なフィールド（記事本文等）がページに混入しないことの確認

```bash
pip install pytest
python -m pytest
```

## ⚠️ 注意事項

- RSSの取得に失敗したURLがあっても、警告を出して他のURLの処理を続けます。
- 有料・会員限定の記事を除外するため、RSSの記事数より実際に選定対象となる件数が少なくなることがあります。同じソースの次の記事で補充しますが、補充できる記事がなければ件数は上限に満たないまま進みます。
- ニュースデータの保存や統計の記録に失敗しても、警告ログを出して処理は継続します。
- 重要度5のニュースがない日はLINE通知を行いません（異常ではありません）。
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
│       ├── daily_news.yml   # 日次実行（workflow_dispatch。運用ではcron-job.orgから毎朝起動、data/stats.jsonとdata/news/の自動コミットを含む）
│       ├── pages.yml        # ニュースページ＋ダッシュボードをGitHub Pagesへデプロイ（公開対象ファイルのみ）
│       └── tests.yml        # pytestによるテストと機密情報スキャン（PR／mainへのpush時）
├── dashboard/
│   └── index.html           # 記事数・カテゴリー分けの可視化ダッシュボード（Chart.js, CDN読み込み）
├── data/
│   ├── stats.json           # 日次統計データ（直近90日分、ワークフローが自動更新）
│   └── news/
│       └── YYYY-MM.json     # 月別の選定ニュースデータ（ワークフローが自動更新）
├── tests/                   # pytestテストスイート
├── config.py                # 定数・環境変数の集約、RSSソース（URL+取得元ラベル）・プロンプトの定義
├── news_fetcher.py          # RSSの取得モジュール（取得元ラベルを各記事に付与）
├── paywall_filter.py        # 有料・会員限定記事の判定モジュール（配信元ドメイン／isAccessibleForFree）
├── note_paywall.py          # note.comの有料記事判定モジュール（無料記事のみ残す）
├── ai_summarizer.py         # Gemini API連携・構造化要約モジュール
├── news_items.py            # Gemini出力JSONのパース・検証、重要度5のLINEメッセージ生成
├── news_store.py            # 選定ニュースの月別JSON保存モジュール
├── page_generator.py        # ニュースページ（トップ＋日別アーカイブ＋週まとめ）の生成モジュール
├── stats_recorder.py        # ダッシュボード用の日次統計データ記録モジュール
├── line_notifier.py         # LINE Messaging API送信モジュール
├── main.py                  # 全体を統括するメイン処理
├── requirements.txt         # 依存ライブラリ一覧
└── README.md                # プロジェクト説明
```
