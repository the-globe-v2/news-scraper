# globe_news_scraper/news_sources/base.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any

from globe_news_scraper.config import Config
from globe_news_scraper.data_providers.news_sources.models import NewsSourceArticleData


class NewsSourceError(Exception):
    """Base exception for NewsSource errors"""


class NewsSource(ABC):
    """
    Abstract base class for a news source.

    This class defines the interface that all news sources must implement, including methods for
    fetching country-specific trending news and retrieving the list of available countries.
    """

    @abstractmethod
    def __init__(self, config: Config):
        """
        Initialize the NewsSource with the provided configuration.

        :param config: Configuration object containing settings for the news source.
        """
        pass

    @abstractmethod
    def get_country_trending_news(self, **kwargs: Any) -> List[NewsSourceArticleData]:
        """
        Fetch trending news articles for a specific country.

        :param kwargs: Additional keyword arguments to customize the news retrieval process.
        :return: A list of NewsSourceArticleData objects representing the trending news articles.
        """
        pass

    @property
    @abstractmethod
    def available_countries(self) -> List[str]:
        """
        Get the list of available countries for this news source.

        :return: A list of country codes available for news retrieval.
        """
        pass
