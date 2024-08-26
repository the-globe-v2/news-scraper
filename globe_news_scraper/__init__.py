# path: globe_news_scraper/__init__.py

import os

import structlog
from typing import List, Dict, Optional, cast, Literal

from globe_news_scraper.config import Config
from globe_news_scraper.logger import configure_logging
from globe_news_scraper.models import GlobeArticle
from globe_news_scraper.monitoring import GlobeScraperTelemetry
from globe_news_scraper.database.mongo_handler import MongoHandler, MongoHandlerError
from globe_news_scraper.data_providers.news_pipeline import NewsPipeline


class GlobeNewsScraper:
    def __init__(self, config: Config) -> None:
        self._config = config

        # Set up and configure logging
        configure_logging(self._config.LOG_LEVEL)
        self._logger = structlog.get_logger()

        self._telemetry = GlobeScraperTelemetry()

        # Try establishing a connection to the MongoDB database
        try:
            self._db_handler = MongoHandler(self._config)
            self._db_handler.initialize()
        except MongoHandlerError as mhe:
            self._logger.critical("Failed to connect to MongoDB", error=str(mhe))
            raise GlobeNewsScraperError("Failed to connect to MongoDB.")

    def scrape_daily(self) -> List[str]:
        """
        Collect news articles from all available sources for the day.

        This method aggregates articles from various news sources,
        creating a comprehensive daily news collection.

        Returns:
            List[GlobeArticle]: A list Mongo ObjectIds representing
            the collected news articles for the day in the DB.
        """
        pipeline = NewsPipeline(self._config, self._telemetry)
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
