import feedparser
import logging

from note_paywall import is_free_note_article, is_note_url


def fetch_news_from_urls(rss_sources: list[dict], max_fetch: int = 20) -> list[dict]:
    """指定されたRSSソースリストから記事を取得し、重複を除外して返す

    各要素は {"url": str, "source": str} の形式を想定する。
    "source" は取得元ラベルで、ダッシュボードの取得元別集計に使用する。

    note.comの記事（source_urlがnote.comドメイン）は、note.comの記事情報API
    で無料記事かどうかを判定し、有料記事は除外する。

    1ソースだけで記事が大量に取れる場合（Googleニュース等）に他のソースが
    まったく反映されなくなるのを防ぐため、1ソースあたりの取得件数を
    max_fetch // ソース数 に制限し、各ソースが公平に反映されるようにする。
    """
    articles = []
    seen_titles = set()

    source_count = len(rss_sources) or 1
    per_source_limit = max(1, max_fetch // source_count)

    for rss_source in rss_sources:
        url = rss_source["url"]
        source_label = rss_source.get("source", url)
        source_article_count = 0

        try:
            feed = feedparser.parse(url)
            logging.info(f"RSS取得中: {url} (取得件数: {len(feed.entries)}件、上限{per_source_limit}件)")

            for entry in feed.entries:
                if source_article_count >= per_source_limit or len(articles) >= max_fetch:
                    break

                title = entry.get("title", "")
                link = entry.get("link", "")

                if not title or title in seen_titles:
                    continue

                if is_note_url(link) and not is_free_note_article(link):
                    logging.info(f"note.comの有料記事のため除外します: {title}")
                    seen_titles.add(title)
                    continue

                seen_titles.add(title)
                articles.append({
                    "title": title,
                    "link": link,
                    "source": source_label,
                })
                source_article_count += 1
        except Exception as e:
            logging.warning(f"RSSの取得に失敗しました ({url}): {e}")

        if len(articles) >= max_fetch:
            break

    logging.info(f"最終取得記事数: {len(articles)}件（ソースあたり上限: {per_source_limit}件、対象ソース数: {source_count}）")
    return articles
