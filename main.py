import logging
from config import RSS_SOURCES_TECH, RSS_SOURCES_INTEREST
from news_fetcher import fetch_news_from_urls
from ai_summarizer import generate_both_summaries
from line_notifier import send_line_messages
from stats_recorder import record_run_stats

logging.basicConfig(level=logging.INFO)

def main():
    try:
        logging.info("1. RSSニュースを取得中...")
        tech_articles = fetch_news_from_urls(RSS_SOURCES_TECH, max_fetch=20)
        interest_articles = fetch_news_from_urls(RSS_SOURCES_INTEREST, max_fetch=20)

        logging.info("2. Geminiで2通分の要約を生成中...")
        tech_summary, interest_summary = generate_both_summaries(tech_articles, interest_articles)

        logging.info("3. ダッシュボード用の統計データを記録中...")
        try:
            record_run_stats(tech_articles, interest_articles, tech_summary, interest_summary)
        except Exception as stats_err:
            # 統計データの記録失敗はダッシュボードのみに影響するため、LINE配信は継続する
            logging.warning(f"統計データの記録に失敗しました（配信処理は継続します）: {stats_err}")

        logging.info("4. LINEへ2通連投送信中...")
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