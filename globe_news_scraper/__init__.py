# path: globe_news_scraper/__init__.py

import structlog
from typing import List

from globe_news_scraper.config import Config
from globe_news_scraper.models import GlobeArticle
from globe_news_scraper.monitoring import GlobeScraperTelemetry
from globe_news_scraper.database.mongo_handler import MongoHandler, MongoHandlerError
from globe_news_scraper.data_providers.news_pipeline import NewsPipeline


class GlobeNewsScraper:
    def __init__(self, config: Config) -> None:
        self._config = config

        self._logger = structlog.get_logger()

        self._telemetry = GlobeScraperTelemetry()

        # Try establishing a connection to the MongoDB database
        try:
            self._db_handler = MongoHandler(self._config)
        except MongoHandlerError as mhe:
            raise GlobeNewsScraperError(f"{str(mhe)}")

    def scrape_daily(self) -> List[str]:
        """
        Collect news articles from all available sources for the day.

        This method aggregates articles from various news sources,
        creating a comprehensive daily news collection.

        Returns:
            List[GlobeArticle]: A list Mongo ObjectIds representing
            the collected news articles for the day in the DB.
        """
        pipeline = NewsPipeline(self._config, self._db_handler, self._telemetry)
        return pipeline.run_pipeline()

    @property
    def telemetry(self) -> GlobeScraperTelemetry:
        """
        Get the telemetry object for the GlobeNewsScraper.

        Returns:
            GlobeScraperTelemetry: The telemetry object.
        """
        return self._telemetry


class GlobeNewsScraperError(Exception):
    """Custom exception for GlobeNewsScraper errors."""
