"""要約の材料（RSS概要）とプロンプト指示に関するテスト。

要約が「記事の紹介文」ではなく中身と結論まで書けるよう、
RSSの概要文を取り込んでGeminiへ渡すことと、プロンプトの指示内容を固定する。
"""
import json
import sys
import types

# CI（tests.yml）は pytest のみをインストールするため、feedparser / requests /
# google-genai が存在しない。対象モジュールの import を通す目的でのみ
# 空スタブを差し込む（このテストではネットワークやAPI呼び出しを行わない）。
for _name in ("feedparser", "requests"):
    sys.modules.setdefault(_name, types.ModuleType(_name))
if "google" not in sys.modules:
    _google = types.ModuleType("google")
    _google.genai = types.ModuleType("google.genai")
    sys.modules["google"] = _google
    sys.modules["google.genai"] = _google.genai

from ai_summarizer import _format_news_content
from config import PROMPT_INTEREST_JSON, PROMPT_TECH_JSON
from news_fetcher import DESCRIPTION_MAX_CHARS, _clean_description
from news_items import parse_articles_json


def test_clean_description_strips_html_and_unescapes():
    entry = {"summary": "<p>新モデルが<strong>公開</strong>された。&amp;性能が向上。</p>"}
    assert _clean_description(entry) == "新モデルが 公開 された。&性能が向上。"


def test_clean_description_falls_back_to_description_field():
    entry = {"description": "説明文です"}
    assert _clean_description(entry) == "説明文です"


def test_clean_description_empty_when_missing():
    assert _clean_description({}) == ""
    assert _clean_description({"summary": "  "}) == ""


def test_clean_description_truncates_long_text():
    entry = {"summary": "あ" * (DESCRIPTION_MAX_CHARS + 100)}
    result = _clean_description(entry)
    assert result.endswith("…")
    assert len(result) <= DESCRIPTION_MAX_CHARS + 1


def test_format_news_content_includes_description():
    articles = [{"title": "タイトル", "link": "https://example.com/a",
                 "source": "出典", "description": "概要テキスト"}]
    content = _format_news_content(articles)
    assert "概要: 概要テキスト" in content


def test_format_news_content_omits_empty_description():
    articles = [{"title": "タイトル", "link": "https://example.com/a",
                 "source": "出典", "description": ""}]
    content = _format_news_content(articles)
    assert "概要:" not in content


def test_prompts_require_conclusion_not_introduction():
    for prompt in (PROMPT_TECH_JSON, PROMPT_INTEREST_JSON):
        # 記事の紹介文ではなく中身と結論まで書く指示があること
        assert "結論" in prompt
        assert "メタ的な説明は書かないでください" in prompt
        # 推測で結論を作らない歯止めがあること
        assert "推測で作り出さないでください" in prompt
        # 概要・本文をそのまま転載しない指示があること（規約・著作権対策）
        assert "そのまま転載せず、必ず自分の言葉で書き直してください" in prompt
        # 旧来の「短くまとめる」指示が残っていないこと
        assert "2〜3個" not in prompt
        assert "60文字以内を目安に簡潔に" not in prompt


def test_parsed_items_never_carry_rss_description():
    """RSS概要は要約の材料専用で、公開データ（記事アイテム）に残らないこと。

    Geminiが概要文をそのまま "description" として返してきても、
    パーサの固定キー（title/url/source/category/summary/importance/tip）
    以外は捨てられるため、記事文章がそのまま公開されることはない。
    """
    sentinel = "RSS概要のセンチネル文"
    fetched = [{"title": "記事タイトル", "link": "https://example.com/a",
                "source": "Zenn", "description": sentinel}]
    gemini_output = json.dumps([{
        "title": "記事タイトル", "url": "https://example.com/a",
        "category": "カテゴリ", "summary": "自分の言葉で書き直した要約",
        "importance": 3, "description": sentinel,
    }])
    items = parse_articles_json(gemini_output, fetched)
    assert len(items) == 1
    assert "description" not in items[0]
    assert sentinel not in json.dumps(items[0], ensure_ascii=False)
