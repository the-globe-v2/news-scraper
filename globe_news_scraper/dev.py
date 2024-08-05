# path: globe_news_scraper/dev.py

import structlog
import time

from globe_news_scraper import GlobeNewsScraper
# from config import get_config
# from bing_news_utils import BingNewsAPI  # type: ignore
# from globe_news_scraper.data_providers.article_builder import ArticleBuilder
# from utils.article_builder import build_article


if __name__ == "__main__":
    # environment = os.getenv("ENV", "development")
    # config = get_config(environment)
    #
    # bing_news = BingNewsAPI(
    #     config.BING_SEARCH_SUBSCRIPTION_KEY, config.BING_SEARCH_ENDPOINT
    # )
    #
    # world_categories = [
    #     "World",
    #     "World_Africa",
    #     "World_Americas",
    #     "World_Asia",
    #     "World_Europe",
    #     "World_MiddleEast",
    # ]

    import json

    logger = structlog.get_logger()

    gns = GlobeNewsScraper()
    start_time = time.time()

    articles = gns.compile_daily_digest()

    end_time = time.time()
    elapsed_time = end_time - start_time

    total_attempted_articles = gns.daily_attempted_articles
    print(f"Fetched {len(articles)} out of {total_attempted_articles} attempted articles.")
    print(f"Elapsed time: {elapsed_time:.2f} seconds")
    for article in articles:
        print(f"Title: {article.title}")
        print(f"URL: {article.url}")
        print(f"Source: {article.source}")
        print("---")