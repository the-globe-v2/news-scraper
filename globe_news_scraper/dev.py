# path: globe_news_scraper/dev.py
import time

from globe_news_scraper import GlobeNewsScraper


# from config import get_config
# from bing_news_utils import BingNewsAPI  # type: ignore
# from globe_news_scraper.data_providers.article_builder import ArticleBuilder
# from utils.article_builder import build_article
def main():
    scraper = GlobeNewsScraper()
    start_time = time.time()
    try:
        scraper.initialize()
        articles = scraper.compile_daily_digest()
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(
            f"Fetched and stored {len(articles)} articles out of {"WIP"} attempts in {elapsed_time} seconds")
        print("breakpoint")
    except Exception as e:
        print(f"An error occurred during initialization: {str(e)}")
        # Handle the error appropriately


if __name__ == "__main__":
    main()
