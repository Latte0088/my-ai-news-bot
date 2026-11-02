import feedparser
import logging

from note_paywall import is_free_note_article, is_note_url
from paywall_filter import get_publisher_host, is_gated_page, is_paywalled_domain

# "paywall_check": "page" のソースで、1回の実行あたりに記事ページを確認する上限件数。
# 会員限定記事が続いても実行時間が際限なく延びないようにするための安全弁。
MAX_PAGE_CHECKS_PER_SOURCE = 10


def fetch_news_from_urls(rss_sources: list[dict], max_fetch: int = 20) -> list[dict]:
    """指定されたRSSソースリストから記事を取得し、重複を除外して返す

    各要素は {"url": str, "source": str} の形式を想定する。
    "source" は取得元ラベルで、ダッシュボードの取得元別集計に使用する。
    任意で "paywall_check": "page" を指定すると、記事ページを取得して会員限定
    記事（schema.orgの isAccessibleForFree が false）を除外する。

    有料・会員限定の記事は次の方法で除外する（除外した記事は取得件数に数えない）。
    - 配信元ドメインが config.PAYWALLED_DOMAINS に含まれる記事
      （Googleニュースは <source> 要素のドメインで判定）
    - note.comの記事: 記事情報APIで有料記事かどうかを判定（note_paywall.py）
    - "paywall_check": "page" のソース: 記事ページで会員限定かどうかを判定

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
        check_pages = rss_source.get("paywall_check") == "page"
        source_article_count = 0
        page_check_count = 0

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

                publisher_host = get_publisher_host(link, entry.get("source", {}).get("href"))
                if is_paywalled_domain(publisher_host):
                    logging.info(f"有料・会員限定の配信元のため除外します ({publisher_host}): {title}")
                    seen_titles.add(title)
                    continue

                if is_note_url(link):
                    if not is_free_note_article(link):
                        logging.info(f"note.comの有料記事のため除外します: {title}")
                        seen_titles.add(title)
                        continue
                elif check_pages:
                    if page_check_count >= MAX_PAGE_CHECKS_PER_SOURCE:
                        logging.info(f"記事ページの確認上限（{MAX_PAGE_CHECKS_PER_SOURCE}件）に達したため、{source_label}の残りの記事はスキップします")
                        break
                    page_check_count += 1
                    if is_gated_page(link):
                        logging.info(f"会員限定の記事のため除外します ({publisher_host}): {title}")
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
