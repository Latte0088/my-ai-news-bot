"""有料・会員限定（ログインが必要）な記事を判定するモジュール。

次の2段階で判定する。note.comの記事は別途 note_paywall.py（価格API）で判定する。

1. 配信元ドメインによる判定（通信なし）
   config.PAYWALLED_DOMAINS に含まれる配信元の記事を除外する。
   Googleニュースの記事URLは news.google.com 上のJavaScript遷移のため、
   RSSの <source> 要素（配信元サイトのURL）からドメインを取得する。

2. 記事ページによる判定（ソースごとに "paywall_check": "page" を指定した場合のみ）
   記事ページのJSON-LDに含まれる schema.org の isAccessibleForFree が
   false の記事（一部または全文が会員限定）を除外する。
   マークアップがないページは無料扱いとする。取得に失敗して判定できなかった
   場合も、記事を落とし過ぎないよう除外しない（警告ログのみ）。
"""
import json
import logging
import re
from urllib.parse import urlparse

import requests

from config import PAYWALLED_DOMAINS

GOOGLE_NEWS_HOST = "news.google.com"
REQUEST_TIMEOUT_SECONDS = 8
USER_AGENT = "Mozilla/5.0 (compatible; my-ai-news-bot)"
LD_JSON_PATTERN = re.compile(
    r"<script[^>]*type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
    re.DOTALL | re.IGNORECASE,
)


def get_host(url: str | None) -> str:
    """URLのホスト名（小文字、ポート除く）を返す。取得できなければ空文字"""
    if not url:
        return ""
    try:
        return (urlparse(url).hostname or "").lower()
    except ValueError:
        return ""


def get_publisher_host(link: str, source_href: str | None = None) -> str:
    """記事の配信元ホストを返す

    Googleニュースの記事（リンクが news.google.com）は、RSSの <source> 要素の
    URLから配信元ホストを取得する。それ以外は記事URLのホストを返す。
    """
    link_host = get_host(link)
    if link_host == GOOGLE_NEWS_HOST:
        return get_host(source_href) or link_host
    return link_host


def is_paywalled_domain(host: str) -> bool:
    """ホストが PAYWALLED_DOMAINS のいずれか（またはそのサブドメイン）か"""
    if not host:
        return False
    return any(host == d or host.endswith("." + d) for d in PAYWALLED_DOMAINS)


def _to_bool(value) -> bool | None:
    """isAccessibleForFree の値（true/false、"True"/"False"等）を真偽値に変換する"""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
    return None


def extract_accessible_for_free(html: str) -> list[bool]:
    """HTML内のJSON-LDから isAccessibleForFree の値をすべて取り出す"""
    values: list[bool] = []
    for match in LD_JSON_PATTERN.finditer(html):
        try:
            data = json.loads(match.group(1))
        except (json.JSONDecodeError, ValueError):
            continue

        stack = [data]
        while stack:
            node = stack.pop()
            if isinstance(node, dict):
                if "isAccessibleForFree" in node:
                    parsed = _to_bool(node["isAccessibleForFree"])
                    if parsed is not None:
                        values.append(parsed)
                stack.extend(node.values())
            elif isinstance(node, list):
                stack.extend(node)
    return values


def is_gated_page(url: str) -> bool | None:
    """記事ページが会員限定（isAccessibleForFree が false）かどうかを判定する

    Returns:
        True:  会員限定（1つでも isAccessibleForFree が false）
        False: 無料、またはマークアップなし
        None:  ページを取得できず判定不能
    """
    try:
        res = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        res.raise_for_status()
    except Exception as e:
        logging.warning(f"記事ページの取得に失敗したため会員限定かの判定をスキップします ({url}): {e}")
        return None

    return any(value is False for value in extract_accessible_for_free(res.text))
