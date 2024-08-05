# globe_news_scraper/news_sources/base.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any


class NewsSourceError(Exception):
    """Base exception for NewsSource errors"""


class NewsSource(ABC):
    @abstractmethod
    def get_trending_topics(self, **kwargs) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_news_by_category(self, category: str, **kwargs) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def search_news(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        pass
