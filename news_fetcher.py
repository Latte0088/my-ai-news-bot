import feedparser

def fetch_news_from_urls(rss_urls: list[str], max_fetch: int = 20) -> list[dict]:
    """指定されたRSS URLリストから記事を取得し、重複を除外して返す"""
    articles = []
    seen_titles = set()

    for url in rss_urls:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            title = entry.get("title", "")
            link = entry.get("link", "")

            if title in seen_titles:
                continue
            seen_titles.add(title)

            articles.append({
                "title": title,
                "link": link
            })
            if len(articles) >= max_fetch:
                break

    return articles[:max_fetch]