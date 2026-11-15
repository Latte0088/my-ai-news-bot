"""data/news/ の月別JSONから GitHub Pages 用のニュースページを生成するモジュール。

生成物:
    _site/index.html            最新日のニュース（重要度4以上を先頭でハイライト）
    _site/archive/YYYY-MM.html  月別アーカイブ（その月の全日分）

著作権ガードレール: ページに描画するのは記事アイテムの
title / url / source / category / summary / importance と日付のみ。
それ以外のフィールド（本文など）は一切出力しない。

使い方:
    python page_generator.py --news-dir data/news --out _site
"""
import argparse
import html
import json
import logging
from pathlib import Path

# ハイライト表示する重要度の下限
HIGHLIGHT_MIN_IMPORTANCE = 4

_PAGE_STYLE = """
body { font-family: sans-serif; max-width: 860px; margin: 0 auto; padding: 16px; line-height: 1.6; color: #222; }
h1 { font-size: 1.5em; }
h2 { font-size: 1.2em; border-bottom: 2px solid #ddd; padding-bottom: 4px; }
.item { border: 1px solid #ddd; border-radius: 8px; padding: 10px 14px; margin: 10px 0; }
.item h3 { margin: 4px 0; font-size: 1.05em; }
.meta { font-size: 0.85em; color: #666; }
.category { background: #eef; border-radius: 4px; padding: 0 6px; }
.importance { color: #b00; font-weight: bold; }
#highlight .item { border-color: #f0b429; background: #fffaf0; }
details { margin-top: 6px; }
nav a { margin-right: 12px; }
""".strip()


def _esc(value) -> str:
    """HTMLエスケープ（属性値にも使えるよう quote=True）"""
    return html.escape(str(value if value is not None else ""), quote=True)


def render_item(item: dict) -> str:
    """記事アイテム1件をHTMLに変換する。許可されたフィールドのみを使う"""
    title = _esc(item.get("title", ""))
    url = _esc(item.get("url", ""))
    source = _esc(item.get("source", ""))
    category = _esc(item.get("category", ""))
    summary = _esc(item.get("summary", ""))
    importance = item.get("importance", "")

    meta_parts = []
    if category:
        meta_parts.append(f'<span class="category">{category}</span>')
    if source:
        meta_parts.append(f'<span class="source">{source}</span>')
    if importance != "":
        meta_parts.append(f'<span class="importance">重要度 {importance}</span>')

    return (
        '<article class="item">'
        f'<div class="meta">{" ".join(meta_parts)}</div>'
        f'<h3><a href="{url}">{title}</a></h3>'
        f"<details><summary>要約を読む</summary><p>{summary}</p></details>"
        "</article>"
    )


def render_compact_item(item: dict) -> str:
    """アーカイブ用のコンパクトな記事アイテム表示（タイトル・カテゴリ・重要度のみ）"""
    title = _esc(item.get("title", ""))
    url = _esc(item.get("url", ""))
    category = _esc(item.get("category", ""))
    importance = item.get("importance", "")

    meta = ""
    if category:
        meta += f'<span class="category">{category}</span> '
    if importance != "":
        meta += f'<span class="importance">重要度 {importance}</span>'

    return f'<li>{meta}<a href="{url}">{title}</a></li>'


def _sorted_by_importance(items: list[dict]) -> list[dict]:
    return sorted(items, key=lambda i: i.get("importance", 0), reverse=True)


def render_index(latest_day: dict | None, months: list[str]) -> str:
    """トップページ（最新日のニュース）のHTMLを生成する"""
    parts = [
        "<!DOCTYPE html>",
        '<html lang="ja">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>AIニュース</title>",
        f"<style>{_PAGE_STYLE}</style>",
        "</head>",
        "<body>",
        "<h1>📰 AIニュース</h1>",
    ]

    if months:
        links = " ".join(
            f'<a href="archive/{_esc(month)}.html">{_esc(month)}</a>' for month in months
        )
        parts.append(f"<nav>過去のニュース: {links}</nav>")

    if latest_day is None:
        parts.append("<p>まだニュースがありません。</p>")
    else:
        date = _esc(latest_day.get("date", ""))
        tech_items = latest_day.get("tech", [])
        interest_items = latest_day.get("interest", [])

        parts.append(f"<p>最新: {date}</p>")

        highlight = _sorted_by_importance(
            [i for i in tech_items + interest_items if i.get("importance", 0) >= HIGHLIGHT_MIN_IMPORTANCE]
        )
        if highlight:
            parts.append('<section id="highlight">')
            parts.append("<h2>⭐ 注目のニュース（重要度4以上）</h2>")
            parts.extend(render_item(item) for item in highlight)
            parts.append("</section>")

        parts.append('<section id="tech">')
        parts.append("<h2>📱 IT・AI技術ニュース</h2>")
        if tech_items:
            parts.extend(render_item(item) for item in tech_items)
        else:
            parts.append("<p>この日の技術ニュースはありません。</p>")
        parts.append("</section>")

        parts.append('<section id="interest">')
        parts.append("<h2>☕ 関心ニュース</h2>")
        if interest_items:
            parts.extend(render_item(item) for item in interest_items)
        else:
            parts.append("<p>この日の関心ニュースはありません。</p>")
        parts.append("</section>")

    parts.append('<p><a href="dashboard/">📊 ダッシュボード</a></p>')
    parts.append("</body>")
    parts.append("</html>")
    return "\n".join(parts) + "\n"


def render_archive(month: str, payload: dict) -> str:
    """月別アーカイブページのHTMLを生成する"""
    parts = [
        "<!DOCTYPE html>",
        '<html lang="ja">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>AIニュース {_esc(month)}</title>",
        f"<style>{_PAGE_STYLE}</style>",
        "</head>",
        "<body>",
        f"<h1>📰 AIニュース {_esc(month)}</h1>",
        '<p><a href="../index.html">← トップへ戻る</a></p>',
    ]

    days = payload.get("days", {})
    for date in sorted(days, reverse=True):
        day = days[date]
        parts.append(f"<h2>{_esc(date)}</h2>")
        for section_key, label in (("tech", "📱 IT・AI技術ニュース"), ("interest", "☕ 関心ニュース")):
            items = day.get(section_key, [])
            if not items:
                continue
            parts.append(f"<h3>{label}</h3>")
            parts.append("<ul>")
            parts.extend(render_compact_item(item) for item in items)
            parts.append("</ul>")

    parts.append("</body>")
    parts.append("</html>")
    return "\n".join(parts) + "\n"


def load_news_data(news_dir: Path) -> dict[str, dict]:
    """data/news/ 配下の月別JSONをすべて読み込み、{month: payload} を返す"""
    payloads: dict[str, dict] = {}
    if not news_dir.exists():
        return payloads
    for path in sorted(news_dir.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logging.warning(f"ニュースファイルの読み込みに失敗しました ({path}): {e}")
            continue
        if isinstance(payload, dict) and isinstance(payload.get("days"), dict):
            payloads[payload.get("month", path.stem)] = payload
    return payloads


def generate(news_dir: Path, out_dir: Path) -> list[Path]:
    """ニュースページ一式を生成し、書き出したファイルのパスのリストを返す"""
    payloads = load_news_data(news_dir)
    months = sorted(payloads, reverse=True)

    latest_day = None
    all_dates = [
        date for payload in payloads.values() for date in payload.get("days", {})
    ]
    if all_dates:
        latest_date = max(all_dates)
        for payload in payloads.values():
            if latest_date in payload.get("days", {}):
                latest_day = payload["days"][latest_date]
                break

    out_dir.mkdir(parents=True, exist_ok=True)
    written = []

    index_path = out_dir / "index.html"
    index_path.write_text(render_index(latest_day, months), encoding="utf-8")
    written.append(index_path)

    if payloads:
        archive_dir = out_dir / "archive"
        archive_dir.mkdir(parents=True, exist_ok=True)
        for month in months:
            archive_path = archive_dir / f"{month}.html"
            archive_path.write_text(render_archive(month, payloads[month]), encoding="utf-8")
            written.append(archive_path)

    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="月別JSONからニュースページを生成する")
    parser.add_argument("--news-dir", type=Path, default=Path("data/news"))
    parser.add_argument("--out", type=Path, default=Path("_site"))
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    written = generate(args.news_dir, args.out)
    for path in written:
        logging.info(f"生成しました: {path}")


if __name__ == "__main__":
    main()
