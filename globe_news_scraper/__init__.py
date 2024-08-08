# path: globe_news_scraper/__init__.py

import os
import logging
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import structlog
from structlog.stdlib import LoggerFactory
from structlog.processors import JSONRenderer, TimeStamper

from globe_news_scraper.config import get_config
from globe_news_scraper.models import GlobeArticle
from globe_news_scraper.monitoring import GlobeScraperTelemetry
from globe_news_scraper.database.mongo_handler import MongoHandler
from globe_news_scraper.data_providers.article_builder import ArticleBuilder
from globe_news_scraper.data_providers.news_sources.factory import NewsSourceFactory
from globe_news_scraper.data_providers.news_sources.base import NewsSource, NewsSourceError


class GlobeNewsScraper:
    def __init__(self, environment: str = "development"):
        self.config = get_config(environment)
        self.telemetry = GlobeScraperTelemetry()
        self.article_builder = ArticleBuilder(self.config, self.telemetry)
        self.news_sources = NewsSourceFactory.get_all_sources(self.config)
        self.db_handler = MongoHandler(self.config)
        self.executor = ThreadPoolExecutor(max_workers=self.config.MAX_SCRAPING_WORKERS)

        self.logger = structlog.get_logger()
        self._configure_logging(self.config.LOG_LEVEL)

    def initialize(self) -> None:
        """
        Initialize the GlobeNewsScraper by connecting to the database and checking the db, collection and required indexes.
        """
        self.db_handler.initialize()

    def compile_daily_digest(self) -> List[GlobeArticle]:
        """
        Collect news articles from all available sources for the day.

        This method aggregates articles from various news sources,
        creating a comprehensive daily news collection.

        Returns:
            List[GlobeArticle]: A list of GlobeArticle objects representing
            the collected news articles for the day.
            int: The number of articles that were attempted to be scraped in the current day.
        """

        all_articles = []
        with ThreadPoolExecutor(max_workers=self.config.MAX_SCRAPING_WORKERS) as executor:
            future_to_topic = {}

            # Iterate over all news sources and fetch trending topics
            for source_api_name, news_source in self.news_sources.items():
                try:
                    trending_topics = news_source.get_trending_topics()
                    for topic in trending_topics:
                        future = executor.submit(self._process_topic, topic, news_source, source_api_name)
                        future_to_topic[future] = topic
                except NewsSourceError as e:
                    self.logger.error(f"Failed to fetch trending topics from {source_api_name}: {e}")

            # Iterate over the completed article requests as they finish
            for future in as_completed(future_to_topic):
                topic = future_to_topic[future]
                try:
                    articles = future.result()

                    # Insert the articles into the database
                    # This is done in a single bulk insert operation to improve performance
                    # Alternatively, articles could be inserted one by one right after they are built
                    # This would allow for more granular error handling, and a more streamlined process
                    self.db_handler.insert_bulk_articles(articles)

                    all_articles.extend(articles)
                    self.logger.info(f"Successfully fetched {len(articles)} articles for topic {topic['name']}")
                except Exception as e:
                    self.logger.error(f"Failed to fetch articles for topic {topic['name']}: {e}")

        return all_articles

    def _process_topic(self, topic, news_source: NewsSource, source_api_name: str) -> List[GlobeArticle]:
        """
       Process a single topic (a list of news articles on a topic) as provided by the news api.

       Args:
           topic (Dict): The topic to process, including all the urls of the articles related to the topic.
           news_source (NewsSource): The news source to use for fetching articles.
           source_api_name (str): The name of the source API.

       Returns:
           List[GlobeArticle]: A list of built GlobeArticle objects for the topic.
       """
        topic_specific_articles = news_source.search_news(topic['query'])

        # Merge the topic metadata with the article metadata, this provides more context to build the GlobeArticle obj
        articles_with_topic_metadata = [{**art, **topic} for art in topic_specific_articles]
        articles = []
        for item in articles_with_topic_metadata:

            # Check if the article already exists in the database and skip scraping if it does
            if self.db_handler.does_article_exist(item['url']):
                self.logger.debug(f"Article already exists in the database, skipping: {item['url']}")
            else:
                article = self._build_article(item, source_api_name)
                if article:
                    articles.append(article)
        return articles

    def _build_article(self, news_item: Dict, source_api_name: str) -> Optional[GlobeArticle]:
        """
           Call ArticleBuilder class to create a GlobeArticle object from a dictionary containing news metadata.

           Args:
               news_item (Dict): The news item to build an article from.
               source_api_name (str): The name of the source API.

           Returns:
               Optional[GlobeArticle]: A built GlobeArticle object, or None if building fails.
           """
        try:
            article = self.article_builder.build(news_item)
            if article:
                article.api_origin = source_api_name
            return article
        except Exception as e:
            self.logger.error(f"Failed to build article for {news_item['url']}: {e}")
            return None

    def _configure_logging(self, log_level: str) -> None:
        """
        Configure logging for the application. This sets up the root logger to log to both a file and the console.

        The foreign_pre_chain is used specifically for log entries that are initiated by the standard Python logging
        framework but are being handled by structlog’s ProcessorFormatter. This ensures that log messages originating
        from libraries not using structlog (like urllib3 in your case) are processed in a similar manner as
        structlog-generated messages.

        params:
            log_level (str): The logging level to set for the root logger.
        """
        logger_level = getattr(logging, log_level.upper(), logging.INFO)

        # Set up the root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logger_level)

        # Ignore DEBUG messages from urllib3
        urllib3_logger = logging.getLogger("urllib3")
        urllib3_logger.setLevel(logging.INFO)

        # Ignore DEBUG messages from asyncio
        asyncio_logger = logging.getLogger("asyncio")
        asyncio_logger.setLevel(logging.INFO)

        # Ignore DEBUG messages from goose3.crawler
        goose3_logger = logging.getLogger("goose3.crawler")
        goose3_logger.setLevel(logging.INFO)

        # Ignore DEBUG messages from pymongo.*
        pymongo_logger = logging.getLogger("pymongo")
        pymongo_logger.setLevel(logging.INFO)

        # Ignore DEBUG messages from charset_normalizer
        charset_normalizer_logger = logging.getLogger("charset_normalizer")
        charset_normalizer_logger.setLevel(logging.INFO)

        # Ensure the logging directory exists
        log_dir = os.path.dirname(f"{self.config.LOGGING_DIR}/globe_news_scraper.log")
        os.makedirs(log_dir, exist_ok=True)

        # Handlers: file and console with different formats
        # File handler logs in JSON format
        file_handler = logging.FileHandler(f"{self.config.LOGGING_DIR}/globe_news_scraper.log")
        file_handler.setLevel(logger_level)
        file_handler.setFormatter(structlog.stdlib.ProcessorFormatter(
            processor=JSONRenderer(),
            foreign_pre_chain=[
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
            ],
        ))

        # Console handler in default structlog format
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logger_level)
        console_handler.setFormatter(structlog.stdlib.ProcessorFormatter(
            processor=structlog.dev.ConsoleRenderer(),
            foreign_pre_chain=[
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
            ],
        ))

        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

        # Configure structlog
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
            ],
            context_class=dict,
            logger_factory=LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,  # type: ignore
            cache_logger_on_first_use=True,
        )

    def get_telemetry(self) -> GlobeScraperTelemetry:
        """
        Get the telemetry object for the GlobeNewsScraper.

        Returns:
            GlobeScraperTelemetry: The telemetry object.
        """
        return self.telemetry
