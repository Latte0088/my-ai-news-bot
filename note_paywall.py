"""note.comの記事が無料記事かどうかを判定するモジュール。

note.comの記事URL（例: https://note.com/<ユーザー名>/n/<記事キー>）から
記事キーを取り出し、note.comの記事情報API
（https://note.com/api/v3/notes/<記事キー>）が返す "price" フィールドで
無料記事（price == 0）か有料記事（price > 0）かを判定する。

このAPIはnote.com側の非公開実装であり、仕様変更やレート制限、一時的な
エラーが起こり得る。判定に失敗した場合は安全側に倒し、有料記事とみなして
除外する（＝「無料記事に限定」という要件を優先する）。
"""
import logging
import re
from urllib.parse import urlparse

import requests

NOTE_API_URL_TEMPLATE = "https://note.com/api/v3/notes/{key}"
NOTE_KEY_PATTERN = re.compile(r"/n/([A-Za-z0-9]+)/?$")
REQUEST_TIMEOUT_SECONDS = 10


def is_note_url(url: str) -> bool:
    """URLがnote.comのドメインかどうかを判定する"""
    try:
        netloc = urlparse(url).netloc
    except ValueError:
        return False
    return netloc == "note.com" or netloc.endswith(".note.com")


def extract_note_key(url: str) -> str | None:
    """note.comの記事URLから記事キー（例: n011cb7b981da）を取り出す"""
    try:
        path = urlparse(url).path
    except ValueError:
        return None
    match = NOTE_KEY_PATTERN.search(path)
    return match.group(1) if match else None


def is_free_note_article(url: str) -> bool:
    """note.comの記事が無料記事かどうかを判定する

    記事キーの取得やAPI呼び出しに失敗した場合は、安全側に倒して
    False（＝除外対象）を返す。
    """
    key = extract_note_key(url)
    if not key:
        logging.warning(f"note.comの記事キーを取得できませんでした。除外します: {url}")
        return False

    try:
        res = requests.get(NOTE_API_URL_TEMPLATE.format(key=key), timeout=REQUEST_TIMEOUT_SECONDS)
        res.raise_for_status()
        price = res.json().get("data", {}).get("price", 0)
        return price == 0
    except Exception as e:
        logging.warning(f"note.comの価格判定に失敗したため除外します ({url}): {e}")
        return False
