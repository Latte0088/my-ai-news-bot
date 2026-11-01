import logging
from config import RSS_SOURCES_TECH, RSS_SOURCES_INTEREST, REPO_NAME
from news_fetcher import fetch_news_from_urls
from ai_summarizer import generate_both_summaries, generate_both_email_summaries, get_current_date_str
from line_notifier import send_line_messages
from stats_recorder import record_run_stats
from email_formatter import build_html_email
from gmail_notifier import send_html_email, is_gmail_configured

logging.basicConfig(level=logging.INFO)

def main():
    try:
        logging.info("1. RSSニュースを取得中...")
        tech_articles = fetch_news_from_urls(RSS_SOURCES_TECH, max_fetch=20)
        interest_articles = fetch_news_from_urls(RSS_SOURCES_INTEREST, max_fetch=20)

        logging.info("2. Geminiで2通分の要約を生成中（LINE向け）...")
        tech_summary, interest_summary = generate_both_summaries(tech_articles, interest_articles)

        logging.info("3. ダッシュボード用の統計データを記録中...")
        try:
            record_run_stats(tech_articles, interest_articles, tech_summary, interest_summary)
        except Exception as stats_err:
            # 統計データの記録失敗はダッシュボードのみに影響するため、LINE配信は継続する
            logging.warning(f"統計データの記録に失敗しました（配信処理は継続します）: {stats_err}")

        logging.info("4. LINEへ2通連投送信中...")
        send_line_messages([tech_summary, interest_summary])

        logging.info("5. Gmailへの送信を確認中...")
        try:
            if is_gmail_configured():
                logging.info("Geminiで要約を生成中（Gmail向け、各10件）...")
                tech_email_summary, interest_email_summary = generate_both_email_summaries(
                    tech_articles, interest_articles
                )
                date_str = get_current_date_str()
                html_body = build_html_email(tech_email_summary, interest_email_summary, date_str)
                send_html_email(f"🤖 [{REPO_NAME}] ニュース要約 - {date_str}", html_body)
            else:
                logging.info("Gmail設定が未登録のため、Gmail送信をスキップします。")
        except Exception as gmail_err:
            # Gmail送信の失敗はLINE配信・統計記録には影響させない
            logging.warning(f"Gmailへの送信に失敗しました（LINE配信は完了済みのため処理は継続します）: {gmail_err}")

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