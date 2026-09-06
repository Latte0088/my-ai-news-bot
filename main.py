import logging
from news_fetcher import fetch_latest_news
from ai_summarizer import generate_summary
from line_notifier import send_line_message

logging.basicConfig(level=logging.INFO)

def main():
    try:
        logging.info("ニュースを取得中...")
        articles = fetch_latest_news()

        logging.info("Geminiで要約を生成中...")
        summary_text = generate_summary(articles)

        logging.info("LINEメッセージを送信中...")
        send_line_message(summary_text)
        logging.info("すべての処理が正常に完了しました。")

    except Exception as e:
        error_msg = f"【自動実行エラー】ニュース配信プログラムでエラーが発生しました:\n{str(e)}"
        logging.error(error_msg)
        try:
            # エラー発生時もLINEに通知する（要求仕様3-A）
            send_line_message(error_msg)
        except Exception as line_err:
            logging.error(f"LINEエラー通知にも失敗しました: {line_err}")

if __name__ == "__main__":
    main()