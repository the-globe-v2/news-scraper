# globe_news_scraper/news_sources/base.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any

from globe_news_scraper.config import Config


class NewsSourceError(Exception):
    """Base exception for NewsSource errors"""


class NewsSource(ABC):
    @abstractmethod
    def __init__(self, config: Config):
        pass

    @abstractmethod
    def get_trending_topics(self, **kwargs: Any) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_news_by_category(self, category: str, **kwargs: Any) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def search_news(self, query: str, **kwargs: Any) -> List[Dict[str, Any]]:
        pass
