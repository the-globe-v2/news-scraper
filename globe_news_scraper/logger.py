# path: globe_news_scraper/logger.py

import os
import re
import sys
import logging
from logging import LogRecord
from logging.handlers import RotatingFileHandler

import structlog


class WarningFilter(logging.Filter):
    """
    goose3 logs a warning when it can't resolve the publishing date to UTC.
    This filter removes that warning as GNS gets its pub timestamps from the NewsSources regardless.
    """

    def filter(self, record: LogRecord) -> bool:
        return not re.match(r'Publish date \d+ could not be resolved to UTC', record.getMessage())


def configure_logging(log_level: str, logging_dir: str = 'logs', environment: str = 'dev') -> None:
    logger_level = logging.INFO if environment == 'prod' else getattr(logging, log_level.upper(), logging.INFO)

    # Configure logging
    logging.basicConfig(level=logger_level)

    # Ignore DEBUG messages from specific loggers
    for logger_name in ['urllib3', 'asyncio', 'goose3.crawler', 'pymongo', 'charset_normalizer']:
        logging.getLogger(logger_name).setLevel(logging.INFO)

    # Remove the warning about publish date not being resolved to UTC
    logging.getLogger('goose3.crawler').addFilter(WarningFilter())

    # Ensure the logging directory exists
    log_dir = os.path.dirname(f'{logging_dir}/globe_news_scraper.log')
    os.makedirs(log_dir, exist_ok=True)

    # Set up log rotation
    file_handler = RotatingFileHandler(
        f'{logging_dir}/globe_news_scraper.log',
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logger_level)

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,  # type: ignore
        cache_logger_on_first_use=True,
    )

    # Set up formatter
    formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.dev.ConsoleRenderer() if environment == 'dev' else structlog.processors.JSONRenderer(),
    )

    # Add handler to the root logger
    root_logger = logging.getLogger()
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    root_logger.addHandler(file_handler)


def log_exception(logger, exc_info, **kwargs):
    """
    Log an exception with additional context.

    Args:
        logger: The logger to use.
        exc_info: The exception info tuple.
        **kwargs: Additional context to add to the log entry.
    """
    logger.exception(
        "An error occurred",
        exc_info=exc_info,
        stack_info=True,
        **kwargs
    )
