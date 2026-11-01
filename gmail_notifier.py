"""Gmail SMTP（アプリパスワード）でHTMLメールを送信するモジュール。

GMAIL_ADDRESS / GMAIL_APP_PASSWORD が未設定の場合は、Gmail通知自体を
スキップする（LINE配信のみの既存運用を壊さないための任意機能として扱う）。
"""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import GMAIL_ADDRESS, GMAIL_APP_PASSWORD

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465


def is_gmail_configured() -> bool:
    """Gmail送信に必要な環境変数が設定されているかどうか"""
    return bool(GMAIL_ADDRESS and GMAIL_APP_PASSWORD)


def send_html_email(subject: str, html_body: str) -> None:
    """GMAIL_ADDRESS宛にHTMLメールを送信する（送信元・送信先は同一アドレス）

    GMAIL_ADDRESS / GMAIL_APP_PASSWORD が未設定の場合は何もせず終了する。
    """
    if not is_gmail_configured():
        logging.info("GMAIL_ADDRESS/GMAIL_APP_PASSWORDが未設定のため、Gmail送信をスキップします。")
        return

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = GMAIL_ADDRESS
    message["To"] = GMAIL_ADDRESS
    message.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_ADDRESS, [GMAIL_ADDRESS], message.as_string())

    logging.info(f"Gmailへの送信が完了しました（宛先: {GMAIL_ADDRESS}）。")
