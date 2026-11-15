"""data/news/ の月別JSONから GitHub Pages 用のニュースページを生成するモジュール。

生成物:
    _site/index.html              最新日のニュース（重要度4以上を先頭でハイライト）
    _site/archive/YYYY-MM-DD.html 日別アーカイブ（その日のニュース一覧）
    _site/weekly/YYYY-Www.html    週まとめ（その週の重要度4以上を集約）

著作権ガードレール: ページに描画するのは記事アイテムの
title / url / source / category / summary / importance と日付のみ。
それ以外のフィールド（本文など）は一切出力しない。

使い方:
    python page_generator.py --news-dir data/news --out _site
"""
import argparse
import datetime
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
.item ul { margin: 6px 0; padding-left: 20px; }
nav a { margin-right: 12px; }
""".strip()


def _esc(value) -> str:
    """HTMLエスケープ（属性値にも使えるよう quote=True）"""
    return html.escape(str(value if value is not None else ""), quote=True)


def _render_summary(summary) -> str:
    """要約をHTMLに変換する。改行区切りの要点は箇条書き（<ul>）にし、1行だけなら段落にする"""
    lines = []
    for raw in str(summary if summary is not None else "").splitlines():
        line = raw.strip().lstrip("・-• ").strip()
        if line:
            lines.append(line)
    if len(lines) > 1:
        items = "".join(f"<li>{_esc(line)}</li>" for line in lines)
        return f"<ul>{items}</ul>"
    if lines:
        return f"<p>{_esc(lines[0])}</p>"
    return ""


def render_item(item: dict) -> str:
    """記事アイテム1件をHTMLに変換する。許可されたフィールドのみを使う"""
    title = _esc(item.get("title", ""))
    url = _esc(item.get("url", ""))
    source = _esc(item.get("source", ""))
    category = _esc(item.get("category", ""))
    summary_html = _render_summary(item.get("summary", ""))
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
        f'<h3><a href="{url}" target="_blank" rel="noopener noreferrer">{title}</a></h3>'
        f"<details><summary>要約を読む</summary>{summary_html}</details>"
        "</article>"
    )


def _sorted_by_importance(items: list[dict]) -> list[dict]:
    return sorted(items, key=lambda i: i.get("importance", 0), reverse=True)


def _render_day_sections(day: dict) -> list[str]:
    """1日分のニュース（注目ハイライト＋技術・関心セクション）のHTML部品を返す"""
    tech_items = day.get("tech", [])
    interest_items = day.get("interest", [])
    parts = []

    highlight = _sorted_by_importance(
        [i for i in tech_items + interest_items if i.get("importance", 0) >= HIGHLIGHT_MIN_IMPORTANCE]
    )
    if highlight:
        parts.append('<section id="highlight">')
        parts.append("<h2>⭐ 注目のニュース（重要度4以上）</h2>")
        parts.extend(render_item(item) for item in highlight)
        parts.append("</section>")

    # 注目のニュース（重要度4以上）に載せた記事は、下のセクションでは繰り返さない
    tech_rest = [i for i in tech_items if i.get("importance", 0) < HIGHLIGHT_MIN_IMPORTANCE]
    interest_rest = [i for i in interest_items if i.get("importance", 0) < HIGHLIGHT_MIN_IMPORTANCE]

    parts.append('<section id="tech">')
    parts.append("<h2>📱 IT・AI技術ニュース</h2>")
    if tech_rest:
        parts.extend(render_item(item) for item in tech_rest)
    elif tech_items:
        parts.append("<p>この日の技術ニュースは、すべて上の「注目のニュース」に掲載しています。</p>")
    else:
        parts.append("<p>この日の技術ニュースはありません。</p>")
    parts.append("</section>")

    parts.append('<section id="interest">')
    parts.append("<h2>☕ 関心ニュース</h2>")
    if interest_rest:
        parts.extend(render_item(item) for item in interest_rest)
    elif interest_items:
        parts.append("<p>この日の関心ニュースは、すべて上の「注目のニュース」に掲載しています。</p>")
    else:
        parts.append("<p>この日の関心ニュースはありません。</p>")
    parts.append("</section>")

    return parts


def _page_head(title: str) -> list[str]:
    return [
        "<!DOCTYPE html>",
        '<html lang="ja">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{_esc(title)}</title>",
        f"<style>{_PAGE_STYLE}</style>",
        "</head>",
        "<body>",
    ]


def render_index(latest_day: dict | None, dates: list[str], weeks: list | None = None) -> str:
    """トップページ（最新日のニュース）のHTMLを生成する。datesは新しい順の日付一覧、weeksは (週キー, 短い期間ラベル) の新しい順リスト"""
    parts = _page_head("AIニュース")
    parts.append("<h1>📰 AIニュース</h1>")

    latest_date = latest_day.get("date", "") if latest_day else ""
    past_dates = [d for d in dates if d != latest_date][:30]
    if past_dates:
        links = " ".join(
            f'<a href="archive/{_esc(d)}.html">{_esc(d)}</a>' for d in past_dates
        )
        parts.append(f"<nav>過去のニュース: {links}</nav>")

    if weeks:
        links = " ".join(
            f'<a href="weekly/{_esc(key)}.html">{_esc(key)}（{_esc(label)}）</a>'
            for key, label in weeks[:12]
        )
        parts.append(f"<nav>週まとめ: {links}</nav>")

    if latest_day is None:
        parts.append("<p>まだニュースがありません。</p>")
    else:
        parts.append(f"<p>最新: {_esc(latest_date)}</p>")
        parts.extend(_render_day_sections(latest_day))

    parts.append('<p><a href="dashboard/">📊 ダッシュボード</a></p>')
    parts.append("</body>")
    parts.append("</html>")
    return "\n".join(parts) + "\n"


def render_day(date: str, day: dict, prev_date: str | None, next_date: str | None) -> str:
    """日別アーカイブページ（その日のニュース一覧）のHTMLを生成する"""
    parts = _page_head(f"AIニュース {date}")
    parts.append(f"<h1>📰 AIニュース {_esc(date)}</h1>")
    parts.append('<p><a href="../index.html">← トップへ戻る</a></p>')

    parts.extend(_render_day_sections(day))

    nav = []
    if prev_date:
        nav.append(f'<a href="{_esc(prev_date)}.html">← {_esc(prev_date)}</a>')
    if next_date:
        nav.append(f'<a href="{_esc(next_date)}.html">{_esc(next_date)} →</a>')
    if nav:
        parts.append(f"<nav>{' '.join(nav)}</nav>")

    parts.append("</body>")
    parts.append("</html>")
    return "\n".join(parts) + "\n"


def _week_key(date_str: str) -> str:
    """日付文字列（YYYY-MM-DD）からISO週キー（YYYY-Www）を返す"""
    iso = datetime.date.fromisoformat(date_str).isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _week_monday(date_str: str) -> datetime.date:
    d = datetime.date.fromisoformat(date_str)
    return d - datetime.timedelta(days=d.weekday())


def _week_label_short(date_str: str) -> str:
    monday = _week_monday(date_str)
    sunday = monday + datetime.timedelta(days=6)
    return f"{monday.month}/{monday.day}〜{sunday.month}/{sunday.day}"


def _week_label_full(date_str: str) -> str:
    monday = _week_monday(date_str)
    sunday = monday + datetime.timedelta(days=6)
    return f"{monday.year}年{monday.month}月{monday.day}日〜{sunday.month}月{sunday.day}日"


def render_weekly(week_key: str, days_desc: list) -> str:
    """週まとめページ（その週の重要度4以上を日付ごとに集約）のHTMLを生成する。

    days_descは (日付文字列, その日のデータ) のリスト（新しい順）。
    """
    range_label = _week_label_full(days_desc[0][0]) if days_desc else ""
    parts = _page_head(f"週まとめ {week_key}")
    parts.append(f"<h1>🗓 週まとめ {_esc(week_key)}（{_esc(range_label)}）</h1>")
    parts.append('<p><a href="../index.html">← トップへ戻る</a></p>')

    for date_str, day in days_desc:
        highlights = _sorted_by_importance(
            [
                i
                for i in day.get("tech", []) + day.get("interest", [])
                if i.get("importance", 0) >= HIGHLIGHT_MIN_IMPORTANCE
            ]
        )
        if not highlights:
            continue
        parts.append(f"<h2>{_esc(date_str)}</h2>")
        parts.extend(render_item(item) for item in highlights)

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

    days: dict[str, dict] = {}
    for payload in payloads.values():
        for date, day in payload.get("days", {}).items():
            days[date] = day
    dates = sorted(days, reverse=True)
    latest_day = days[dates[0]] if dates else None

    out_dir.mkdir(parents=True, exist_ok=True)
    written = []

    # 週まとめ（重要度4以上が1件以上ある週だけ生成する）
    weeks: dict[str, list] = {}
    for date in dates:
        weeks.setdefault(_week_key(date), []).append((date, days[date]))
    week_links = []
    weekly_dir = out_dir / "weekly"
    for key in sorted(weeks, reverse=True):
        wdays = weeks[key]
        has_highlight = any(
            i.get("importance", 0) >= HIGHLIGHT_MIN_IMPORTANCE
            for _, d in wdays
            for i in d.get("tech", []) + d.get("interest", [])
        )
        if not has_highlight:
            continue
        weekly_dir.mkdir(parents=True, exist_ok=True)
        weekly_path = weekly_dir / f"{key}.html"
        weekly_path.write_text(render_weekly(key, wdays), encoding="utf-8")
        written.append(weekly_path)
        week_links.append((key, _week_label_short(wdays[0][0])))

    index_path = out_dir / "index.html"
    index_path.write_text(render_index(latest_day, dates, week_links), encoding="utf-8")
    written.append(index_path)

    if days:
        archive_dir = out_dir / "archive"
        archive_dir.mkdir(parents=True, exist_ok=True)
        ascending = sorted(days)
        for idx, date in enumerate(ascending):
            prev_date = ascending[idx - 1] if idx > 0 else None
            next_date = ascending[idx + 1] if idx + 1 < len(ascending) else None
            archive_path = archive_dir / f"{date}.html"
            archive_path.write_text(
                render_day(date, days[date], prev_date, next_date), encoding="utf-8"
            )
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
