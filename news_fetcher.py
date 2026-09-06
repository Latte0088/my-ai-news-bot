import feedparser
from config import RSS_URLS, MAX_NEWS_COUNT

def fetch_latest_news() -> list[dict]:
    articles = []
    seen_titles = set()

    for url in RSS_URLS:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            title = entry.get("title", "")
            link = entry.get("link", "")

            # 重複記事の除外
            if title in seen_titles:
                continue
            seen_titles.add(title)

            articles.append({
                "title": title,
                "link": link,
                "published": entry.get("published", "")
            })

            if len(articles) >= MAX_NEWS_COUNT * 2:  # 重複除去用に多めに取得
                break

    return articles[:MAX_NEWS_COUNT * 2]