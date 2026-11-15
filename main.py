import logging
from config import RSS_SOURCES_TECH, RSS_SOURCES_INTEREST, PAGES_URL
from news_fetcher import fetch_news_from_urls
from ai_summarizer import generate_structured_summaries, get_current_date_str
from line_notifier import send_line_messages
from news_items import build_importance5_message
from news_store import save_daily_news, today_jst_str
from stats_recorder import record_run_stats

logging.basicConfig(level=logging.INFO)

def main():
    try:
        logging.info("1. RSSニュースを取得中...")
        tech_articles = fetch_news_from_urls(RSS_SOURCES_TECH, max_fetch=20)
        interest_articles = fetch_news_from_urls(RSS_SOURCES_INTEREST, max_fetch=20)

        logging.info("2. Geminiで構造化要約（JSON）を生成中...")
        summaries = generate_structured_summaries(tech_articles, interest_articles)
        tech_items = summaries["tech"]
        interest_items = summaries["interest"]

        logging.info("3. ニュースデータを月別JSONへ保存中...")
        try:
            save_daily_news(today_jst_str(), tech_items, interest_items)
        except Exception as news_err:
            # ニュースデータの保存失敗はGitHub Pagesの更新のみに影響するため、処理は継続する
            logging.warning(f"ニュースデータの保存に失敗しました（処理は継続します）: {news_err}")

        logging.info("4. ダッシュボード用の統計データを記録中...")
        try:
            record_run_stats(tech_articles, interest_articles, tech_items, interest_items)
        except Exception as stats_err:
            # 統計データの記録失敗はダッシュボードのみに影響するため、処理は継続する
            logging.warning(f"統計データの記録に失敗しました（処理は継続します）: {stats_err}")

        logging.info("5. 重要度5のニュースがあればLINEへ通知中...")
        message = build_importance5_message(
            tech_items + interest_items,
            get_current_date_str(),
            PAGES_URL,
        )
        if message is not None:
            send_line_messages([message])
        else:
            logging.info("重要度5のニュースはないため、LINE通知をスキップします。")

        logging.info("すべての処理が正常に完了しました。")

    except Exception as e:
        error_msg = f"【自動実行エラー】ニュース配信プログラムでエラーが発生しました:\n{str(e)}"
        logging.error(error_msg)
        try:
            send_line_messages([error_msg])
        except Exception as line_err:
            logging.error(f"LINEエラー通知送信失敗: {line_err}")

if __name__ == "__main__":
    main()
