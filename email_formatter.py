"""Gemini要約テキストをHTMLメール本文に変換するモジュール。

ai_summarizer.generate_both_email_summaries() が返す整形済みテキスト
（「1. 【カテゴリ】タイトル / ▪️要点 / 要約 / ▪️記事を読む / URL」の繰り返し）を、
記事カード形式のHTMLに変換する。

Geminiに直接HTMLを生成させていない（プレーンテキストの出力フォーマットを
維持している）ため、テキスト解析でHTML化する。解析に失敗した記事があっても
メール全体の送信が止まらないよう、その記事は生テキストのままフォールバック
表示する。
"""
import html
import logging
import re

ENTRY_START_PATTERN = re.compile(r"^\d+\.\s+", re.MULTILINE)
CATEGORY_TITLE_PATTERN = re.compile(r"^【(.+?)】\s*(.*)$")
URL_PATTERN = re.compile(r"https?://\S+")
READ_MORE_MARKER = "記事を読む"
SUMMARY_MARKER = "要点"


def _split_entries(text: str) -> list[str]:
    """Geminiの出力テキストを記事ブロック単位に分割する"""
    text = (text or "").strip()
    if not text:
        return []

    matches = list(ENTRY_START_PATTERN.finditer(text))
    if not matches:
        # 番号付きの記事リスト形式になっていない場合は、全体を1ブロックとして扱う
        return [text]

    blocks = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[start:end].strip()
        if block:
            blocks.append(block)
    return blocks


def _parse_entry(block: str) -> dict:
    """1記事分のブロックを {category, title, summary, url} に分解する

    解析に失敗した場合（想定フォーマットと異なる場合）は、
    {"raw": block} を返し、呼び出し側で生テキスト表示にフォールバックさせる。
    """
    lines = [line.strip() for line in block.splitlines() if line.strip()]
    if not lines:
        return {"raw": block}

    first_line_match = CATEGORY_TITLE_PATTERN.match(lines[0])
    if not first_line_match:
        return {"raw": block}

    category = first_line_match.group(1).strip()
    title = first_line_match.group(2).strip()

    # ▪️要点 〜 ▪️記事を読む の間を要約本文として扱う
    body_lines = []
    in_summary = False
    url = None

    for line in lines[1:]:
        if SUMMARY_MARKER in line and line.startswith("▪"):
            in_summary = True
            continue
        if READ_MORE_MARKER in line and line.startswith("▪"):
            in_summary = False
            continue
        if in_summary:
            body_lines.append(line)
            continue
        # ▪️記事を読む の後に続くURL行を拾う
        url_match = URL_PATTERN.search(line)
        if url_match:
            url = url_match.group(0)

    if not url:
        # マーカーが期待通りでなかった場合のフォールバック: ブロック内の最初のURL
        url_match = URL_PATTERN.search(block)
        url = url_match.group(0) if url_match else None

    if not title or not url:
        return {"raw": block}

    return {
        "category": category,
        "title": title,
        "summary": "\n".join(body_lines).strip(),
        "url": url,
    }


def parse_summary_text(text: str) -> list[dict]:
    """Geminiの要約テキストを記事情報のリストに変換する"""
    entries = []
    for block in _split_entries(text):
        entries.append(_parse_entry(block))
    return entries


def _render_entry_html(entry: dict) -> str:
    if "raw" in entry:
        # 解析に失敗した記事は、崩さず生テキストのまま表示する
        escaped = html.escape(entry["raw"]).replace("\n", "<br>")
        return f"""
        <div style="margin:0 0 16px;padding:12px 16px;border:1px solid #e1e0d9;border-radius:8px;">
          <p style="margin:0;color:#52514e;font-size:14px;white-space:pre-wrap;">{escaped}</p>
        </div>
        """

    category = html.escape(entry["category"])
    title = html.escape(entry["title"])
    summary = html.escape(entry["summary"]).replace("\n", "<br>")
    url = html.escape(entry["url"], quote=True)

    return f"""
    <div style="margin:0 0 16px;padding:12px 16px;border:1px solid #e1e0d9;border-radius:8px;">
      <span style="display:inline-block;background:#eef4fc;color:#2a78d6;font-size:12px;font-weight:600;padding:2px 8px;border-radius:999px;margin-bottom:6px;">{category}</span>
      <p style="margin:4px 0 8px;font-size:16px;font-weight:600;">
        <a href="{url}" style="color:#0b0b0b;text-decoration:none;">{title}</a>
      </p>
      <p style="margin:0 0 8px;color:#52514e;font-size:14px;line-height:1.6;">{summary}</p>
      <a href="{url}" style="color:#2a78d6;font-size:13px;text-decoration:none;">記事を読む ▸</a>
    </div>
    """


def _render_section_html(heading: str, summary_text: str) -> str:
    entries = parse_summary_text(summary_text)
    if not entries:
        return f"""
        <h2 style="font-size:18px;margin:24px 0 12px;">{html.escape(heading)}</h2>
        <p style="color:#898781;font-size:14px;">本日は対象の記事がありませんでした。</p>
        """

    entries_html = "\n".join(_render_entry_html(e) for e in entries)
    return f"""
    <h2 style="font-size:18px;margin:24px 0 12px;">{html.escape(heading)}</h2>
    {entries_html}
    """


def build_html_email(tech_summary: str, interest_summary: str, date_str: str) -> str:
    """技術ニュース・関心ニュースの要約テキストから、HTMLメール本文全体を組み立てる"""
    try:
        tech_section = _render_section_html("📱 IT・AI技術ニュース", tech_summary)
        interest_section = _render_section_html("☕ 関心ニュース・トピック", interest_summary)
    except Exception as e:
        # HTML組み立て自体に失敗した場合は、プレーンテキストをそのまま貼り付けた
        # 最低限のHTMLにフォールバックする（メール送信自体は止めない）
        logging.warning(f"要約のHTML変換に失敗したため、プレーンテキストでフォールバックします: {e}")
        fallback = html.escape(f"{tech_summary}\n\n{interest_summary}").replace("\n", "<br>")
        return f"""<!doctype html><html><head><meta charset="utf-8"></head><body><p>{fallback}</p></body></html>"""

    return f"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
  </head>
  <body style="margin:0;padding:24px;background:#f9f9f7;font-family:system-ui,-apple-system,'Segoe UI',sans-serif;color:#0b0b0b;">
    <div style="max-width:640px;margin:0 auto;background:#fcfcfb;border-radius:12px;padding:24px;">
      <h1 style="font-size:20px;margin:0 0 4px;">🤖 ニュース要約</h1>
      <p style="margin:0 0 16px;color:#898781;font-size:13px;">{html.escape(date_str)}</p>
      {tech_section}
      {interest_section}
    </div>
  </body>
</html>"""
