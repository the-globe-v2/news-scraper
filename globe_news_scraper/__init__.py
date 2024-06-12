import json

import structlog
import logging
from structlog.stdlib import LoggerFactory
from structlog.processors import JSONRenderer, TimeStamper

from globe_news_scraper.config import get_config
from globe_news_scraper.news_harvest.article_builder import ArticleBuilder


class GlobeNewsScraper:
    def __init__(self, environment: str = "development"):
        config = get_config(environment)
        self.config = config
        self.article_builder = ArticleBuilder(config)

        self.__configure_logging(config.LOG_LEVEL)
        self.logger = structlog.get_logger()

    def daily_harvest(self):
        """
        Harvest trending news articles from today's date and build GlobeArticle objects.
        """

        # bing_news = BingNewsAPI( blah blah blah )
        with open("bing_news.json", "r") as news_file:
            api_response = json.load(news_file)

        articles = []
        for i, article in enumerate(api_response):
            try:
                art = self.article_builder.build(article["url"])
                articles.append(art)
            except Exception as e:
                self.logger.error(f"Failed to build article for {article['url']}: {e}")

        return articles

    def __configure_logging(self, log_level: str) -> None:
        """
        Configure logging for the application. This sets up the root logger to log to both a file and the console.

        The foreign_pre_chain is used specifically for log entries that are initiated by the standard Python logging
        framework but are being handled by structlog’s ProcessorFormatter. This ensures that log messages originating
        from libraries not using structlog (like urllib3 in your case) are processed in a similar manner as
        structlog-generated messages.

        params:
            log_level (str):
        """
        logger_level = getattr(logging, log_level.upper(), logging.INFO)

        # Set up the root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logger_level)

        # Ignore DEBUG messages from urllib3
        urllib3_logger = logging.getLogger("urllib3")
        urllib3_logger.setLevel(logging.INFO)

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
