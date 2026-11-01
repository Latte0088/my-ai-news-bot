import feedparser
import logging


def fetch_news_from_urls(rss_sources: list[dict], max_fetch: int = 20) -> list[dict]:
    """指定されたRSSソースリストから記事を取得し、重複を除外して返す

    各要素は {"url": str, "source": str} の形式を想定する。
    "source" は取得元ラベルで、ダッシュボードの取得元別集計に使用する。
    """
    articles = []
    seen_titles = set()

    for rss_source in rss_sources:
        url = rss_source["url"]
        source_label = rss_source.get("source", url)

        try:
            feed = feedparser.parse(url)
            logging.info(f"RSS取得中: {url} (取得件数: {len(feed.entries)}件)")

            for entry in feed.entries:
                title = entry.get("title", "")
                link = entry.get("link", "")

                if not title or title in seen_titles:
                    continue

                seen_titles.add(title)
                articles.append({
                    "title": title,
                    "link": link,
                    "source": source_label,
                })

                if len(articles) >= max_fetch:
                    break
        except Exception as e:
            logging.warning(f"RSSの取得に失敗しました ({url}): {e}")

        if len(articles) >= max_fetch:
            break

    logging.info(f"最終取得記事数: {len(articles)}件")
    return articles
