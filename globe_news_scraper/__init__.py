# path: globe_news_scraper/__init__.py

import structlog
from typing import List

from globe_news_scraper.config import Config
from globe_news_scraper.models import GlobeArticle
from globe_news_scraper.monitoring import GlobeScraperTelemetry
from globe_news_scraper.database.mongo_handler import MongoHandler, MongoHandlerError
from globe_news_scraper.data_providers import NewsPipeline


class GlobeNewsScraper:
    """
    Main class for the Globe News Scraper application.

    This class is responsible for orchestrating the news scraping process,
    handling telemetry, and interacting with the database.
    """

    def __init__(self, config: Config) -> None:
        """
        Initialize the GlobeNewsScraper with the provided configuration.

        :param config: Configuration object containing settings for the scraper.
        :raises GlobeNewsScraperError: If there's an issue connecting to the MongoDB database.
        """
        self._config = config

        # Initialize the logger for the scraper
        self._logger = structlog.get_logger()

        # Initialize telemetry for monitoring purposes
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

        :return: A list of MongoDB ObjectIds representing the collected news articles for the day.
        :rtype: List[str]
        """
        pipeline = NewsPipeline(self._config, self._db_handler, self._telemetry)
        return pipeline.run_pipeline()

    @property
    def telemetry(self) -> GlobeScraperTelemetry:
        """
        Get the telemetry object for the GlobeNewsScraper.

        :return: The telemetry object.
        :rtype: GlobeScraperTelemetry
        """
        return self._telemetry


class GlobeNewsScraperError(Exception):
    """
    Custom exception for errors related to GlobeNewsScraper.

    This exception is raised when there are issues during the scraper's operation,
    such as database connection failures.
    """
