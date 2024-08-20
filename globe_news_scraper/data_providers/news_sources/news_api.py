# globe_news_scraper/news_sources/base.py
from typing import List, Dict, Any

from globe_news_scraper.config import Config
from globe_news_scraper.data_providers.news_sources.base import NewsSource, NewsSourceError


class NewsAPIError(NewsSourceError):
    """Base exception for NewsSource errors"""


class NewsAPISource(NewsSource):
    def __init__(self, config: Config):
        # WIP
        pass

    def get_country_trending_news(self, **kwargs: Any) -> List[Dict[str, Any]]:
        # WIP
        return []
