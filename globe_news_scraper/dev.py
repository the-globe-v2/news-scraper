# path: globe_news_scraper/dev.py
import os
import structlog
from datetime import datetime

from globe_news_scraper import GlobeNewsScraper
# from config import get_config
# from bing_news_utils import BingNewsAPI  # type: ignore
# from globe_news_scraper.news_harvest.article_builder import ArticleBuilder
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
    articles = gns.daily_harvest()


    print(articles)
