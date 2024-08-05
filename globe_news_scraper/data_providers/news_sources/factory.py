# globe_news_scraper/news_sources/factory.py
from typing import Dict, Type

from globe_news_scraper.data_providers.news_sources.base import NewsSource
from globe_news_scraper.data_providers.news_sources.bing_news import BingNewsSource


# NOTE: If the news factory is ever to support more sources, the API response objects need to be parsed and standardized
class NewsSourceFactory:
    _sources: Dict[str, Type[NewsSource]] = {
        'bing': BingNewsSource,
    }

    @classmethod
    def create(cls, source_type: str, config) -> NewsSource:
        source_class = cls._sources.get(source_type.lower())
        if source_class:
            return source_class(config)
        else:
            raise ValueError(f"Unsupported news source: {source_type}")

    @classmethod
    def get_all_sources(cls, config) -> Dict[str, NewsSource]:
        return {name: source_class(config) for name, source_class in cls._sources.items()}
