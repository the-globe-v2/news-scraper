# path: globe_news_scraper/logger.py

import os
import re
import logging
from logging import LogRecord

import structlog
from structlog.stdlib import LoggerFactory
from structlog.processors import JSONRenderer, TimeStamper


class WarningFilter(logging.Filter):
    """
    goose3 logs a warning when it can't resolve the publishing date to UTC.
    This filter removes that warning as GNS gets its pub timestamps from the NewsSources regardless.
    """

    def filter(self, record: LogRecord) -> bool:
        return not re.match(r'Publish date \d+ could not be resolved to UTC', record.getMessage())


def configure_logging(log_level: str, logging_dir: str = 'logs') -> None:
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
    urllib3_logger = logging.getLogger('urllib3')
    urllib3_logger.setLevel(logging.INFO)

    # Ignore DEBUG messages from asyncio
    asyncio_logger = logging.getLogger('asyncio')
    asyncio_logger.setLevel(logging.INFO)

    # Ignore DEBUG messages from goose3.crawler
    goose3_logger = logging.getLogger('goose3.crawler')
    goose3_logger.setLevel(logging.INFO)

    # Remove the warning about publish date not being resolved to UTC
    logger = logging.getLogger('goose3.crawler')
    logger.addFilter(WarningFilter())

    # Ignore DEBUG messages from pymongo.*
    pymongo_logger = logging.getLogger('pymongo')
    pymongo_logger.setLevel(logging.INFO)

    # Ignore DEBUG messages from charset_normalizer
    charset_normalizer_logger = logging.getLogger('charset_normalizer')
    charset_normalizer_logger.setLevel(logging.INFO)

    # Ensure the logging directory exists
    log_dir = os.path.dirname(f'{logging_dir}/globe_news_scraper.log')
    os.makedirs(log_dir, exist_ok=True)

    # Handlers: file and console with different formats
    # File handler logs in JSON format
    file_handler = logging.FileHandler(f'{logging_dir}/globe_news_scraper.log')
    file_handler.setLevel(logger_level)
    file_handler.setFormatter(structlog.stdlib.ProcessorFormatter(
        processor=JSONRenderer(),
        foreign_pre_chain=[
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            TimeStamper(fmt='iso'),
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
            TimeStamper(fmt='iso'),
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
            TimeStamper(fmt='iso'),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,  # type: ignore
        cache_logger_on_first_use=True,
    )
