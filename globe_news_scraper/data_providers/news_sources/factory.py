# globe_news_scraper/news_sources/factory.py
from typing import List, Type

from typing import List, Type

from globe_news_scraper.config import Config
from globe_news_scraper.data_providers.news_sources.base import NewsSource
from globe_news_scraper.data_providers.news_sources.bing_news import BingNewsSource


# NOTE: If the news factory is ever to support more sources, the API response objects need to be serialized
class NewsSourceFactory:
    """
    Factory class for creating instances of all available news sources.

    This factory is responsible for managing and initializing them.
    """
    _sources: List[Type[NewsSource]] = [BingNewsSource]

    @classmethod
    def get_all_sources(cls, config: Config) -> List[NewsSource]:
        """
        Returns and initializes all available news sources.

        :param config: The globe base configuration object.
        :return: An initialized list of all available news sources.
        """
        return [source_class(config) for source_class in cls._sources]
