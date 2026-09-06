import feedparser
import logging

def fetch_news_from_urls(rss_urls: list[str], max_fetch: int = 20) -> list[dict]:
    """指定されたRSS URLリストから記事を取得し、重複を除外して返す"""
    articles = []
    seen_titles = set()

    for url in rss_urls:
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
                    "link": link
                })

                if len(articles) >= max_fetch:
                    break
        except Exception as e:
            logging.warning(f"RSSの取得に失敗しました ({url}): {e}")

        if len(articles) >= max_fetch:
            break

    logging.info(f"最終取得記事数: {len(articles)}件")
    return articles