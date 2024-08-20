# path: globe_news_scraper/dev.py
# type: ignore
import time

from globe_news_scraper import GlobeNewsScraper


# from config import get_config
# from bing_news_utils import BingNewsAPI  # type: ignore
# from globe_news_scraper.data_providers.article_builder import ArticleBuilder
# from utils.article_builder import build_article
def main() -> None:
    scraper = GlobeNewsScraper()
    start_time = time.time()
    try:
        articles = scraper.scrape_daily()
        end_time = time.time()
        elapsed_time = end_time - start_time

        scraper.telemetry.log_article_stats()
        scraper.telemetry.log_request_summary()
        scraper.telemetry.log_all_request_status_codes()

        print(
            f"Fetched and stored {len(articles)} articles out of "
            f"{scraper.telemetry.article_counter.get_total_attempted_articles()} attempts in {elapsed_time} seconds")
        print("breakpoint")
    except Exception as e:
        print(f"An error occurred during initialization: {str(e)}")


if __name__ == "__main__":
    main()
