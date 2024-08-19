# globe_news_scraper/news_sources/base.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any

from globe_news_scraper.config import Config
from globe_news_scraper.data_providers.news_sources.models import NewsSourceArticleData


class NewsSourceError(Exception):
    """Base exception for NewsSource errors"""


class NewsSource(ABC):
    @abstractmethod
    def __init__(self, config: Config):
        pass

    @abstractmethod
    def get_country_trending_news(self, **kwargs: Any) -> List[NewsSourceArticleData]:
        pass

    @property
    @abstractmethod
    def available_countries(self) -> List[str]:
        pass
