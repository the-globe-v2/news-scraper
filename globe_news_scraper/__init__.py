import os
import structlog
import logging
from typing import List, Dict
from structlog.stdlib import LoggerFactory
from structlog.processors import JSONRenderer, TimeStamper

from globe_news_scraper.config import get_config
from globe_news_scraper.models import GlobeArticle
from globe_news_scraper.data_providers.article_builder import ArticleBuilder
from globe_news_scraper.data_providers.news_sources.factory import NewsSourceFactory
from globe_news_scraper.data_providers.news_sources.base import NewsSource, NewsSourceError


class GlobeNewsScraper:
    def __init__(self, environment: str = "development"):
        self.config = get_config(environment)
        self.article_builder = ArticleBuilder(self.config)
        self.news_sources = NewsSourceFactory.get_all_sources(self.config)

        self._daily_attempted_articles = 0  # tracks number of article urls provided to scraper

        self._configure_logging(self.config.LOG_LEVEL)
        self.logger = structlog.get_logger()

    def compile_daily_digest(self):
        """
        Collect news articles from all available sources for the day.

        This method aggregates articles from various news sources,
        creating a comprehensive daily news collection.

        Returns:
            List[GlobeArticle]: A list of GlobeArticle objects representing
            the collected news articles for the day.
        """

        self._daily_attempted_articles = 0
        all_articles = []
        for source_api_name, news_source in self.news_sources.items():
            try:
                trending_topics = self._fetch_trending_news(news_source)
                articles = []
                for topic in trending_topics:
                    topic_specific_articles = news_source.search_news(topic['query'])
                    self._daily_attempted_articles += len(topic_specific_articles)  # Track total attempted articles
                    articles_with_topic_metadata = [
                        # Merge topic metadata with article metadata
                        {**art, **topic} for art in topic_specific_articles
                    ]
                    articles.extend(
                        self._build_articles_from_api_response(articles_with_topic_metadata, source_api_name))
                all_articles.extend(articles)
            except NewsSourceError as e:
                self.logger.error(f"Failed to fetch trending topics from {source_api_name}: {e}")

        return all_articles

    def _fetch_trending_news(self, news_source: NewsSource) -> List[Dict]:
        """Fetch trending news topics from a news source object."""
        try:
            return news_source.get_trending_topics()
        except NewsSourceError as e:
            self.logger.error(f"Error fetching trending topics: {e}")
            return []

    def _build_articles_from_api_response(self, news_items: List[Dict], source_api_name: str) -> List[GlobeArticle]:
        """
        Build GlobeArticle objects from a list of news items, adding additional information
        such as the API the news originated from, the topic, and whether it is breaking news.

        Args:
            news_items (List[Dict]): A list of news items to build GlobeArticle objects from.
            source_api_name (str): The name of the news source API.

        Returns:
            List[GlobeArticle]: A list of GlobeArticle objects built from the news items.
        """
        articles = []
        for news_item in news_items:
            try:
                article = self.article_builder.build(news_item)

                if article:
                    # Add additional information to the article provided by the news API
                    article.api_origin = source_api_name

                    articles.append(article)
            except Exception as e:
                self.logger.error(f"Failed to build article for {news_item['url']}: {e}")
        return articles

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

        # Ignore DEBUG messages from goose3.crawler
        goose3_logger = logging.getLogger("goose3.crawler")
        goose3_logger.setLevel(logging.INFO)

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

    @property
    def daily_attempted_articles(self) -> int:
        """
        Get the number of articles attempted to be scraped today.

        Returns:
            int: The number of articles that were attempted to be scraped in the current day.
        """
        return self._daily_attempted_articles
