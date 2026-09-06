import requests
from config import LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID

def send_line_messages(messages: list[str]) -> None:
    """最大5件までのメッセージを配列で受け取り、1回のリクエストでまとめて送信する"""
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }
    
    message_objects = [{"type": "text", "text": msg} for msg in messages]

    payload = {
        "to": LINE_USER_ID,
        "messages": message_objects
    }
    
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()