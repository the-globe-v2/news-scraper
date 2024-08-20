# globe_news_scraper/news_sources/factory.py
from typing import List, Type

from globe_news_scraper.config import Config
from globe_news_scraper.data_providers.news_sources.base import NewsSource
from globe_news_scraper.data_providers.news_sources.bing_news import BingNewsSource


# NOTE: If the news factory is ever to support more sources, the API response objects need to be serialized
class NewsSourceFactory:
    _sources: List[Type[NewsSource]] = [BingNewsSource]

    @classmethod
    def get_all_sources(cls, config: Config) -> List[NewsSource]:
        """
        Returns and initializes all available news sources.

        Args:
            config (Config): The globe base configuration object.

        Returns:
            List[NewsSource]: An initialized list of all available news sources.
        """
        return [source_class(config) for source_class in cls._sources]
