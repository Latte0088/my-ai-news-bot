import logging
from config import RSS_URLS_TECH, RSS_URLS_INTEREST
from news_fetcher import fetch_news_from_urls
from ai_summarizer import generate_both_summaries
from line_notifier import send_line_messages

logging.basicConfig(level=logging.INFO)

def main():
    try:
        logging.info("1. RSSニュースを取得中...")
        tech_articles = fetch_news_from_urls(RSS_URLS_TECH, max_fetch=20)
        interest_articles = fetch_news_from_urls(RSS_URLS_INTEREST, max_fetch=20)

        logging.info("2. Geminiで2通分の要約を生成中...")
        tech_summary, interest_summary = generate_both_summaries(tech_articles, interest_articles)

        logging.info("3. LINEへ2通連投送信中...")
        send_line_messages([tech_summary, interest_summary])
        logging.info("すべての配信処理が正常に完了しました。")

    except Exception as e:
        error_msg = f"【自動実行エラー】ニュース配信プログラムでエラーが発生しました:\n{str(e)}"
        logging.error(error_msg)
        try:
            send_line_messages([error_msg])
        except Exception as line_err:
            logging.error(f"LINEエラー通知送信失敗: {line_err}")

if __name__ == "__main__":
    main()