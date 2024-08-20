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


def configure_logging(log_level: str, logging_dir: str = 'logs') -> None:
    """
    Configure logging for the application. This sets up the root logger to log to both a file and the console.

    Args:
        log_level (str): The logging level to set for the root logger.
        logging_dir (str): The directory where log files will be stored.
    """
    logger_level = getattr(logging, log_level.upper(), logging.INFO)

    # Set up the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logger_level)

    # Ignore DEBUG messages from specific loggers
    for logger_name in ['urllib3', 'asyncio', 'goose3.crawler', 'pymongo', 'charset_normalizer']:
        logging.getLogger(logger_name).setLevel(logging.INFO)

    # Remove the warning about publish date not being resolved to UTC
    logger = logging.getLogger('goose3.crawler')
    logger.addFilter(WarningFilter())

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

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logger_level)

    # Define shared processors
    shared_processors = [
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    # Determine the log output format by the terminal type, isatty() returns True if the file descriptor is an open tty
    if sys.stderr.isatty():
        # Development: Pretty printing
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(),
        ]
    else:
        # Production: JSON output
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]

    # Configure structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Set up formatters
    file_formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
        foreign_pre_chain=shared_processors,
    )
    console_formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.dev.ConsoleRenderer(),
        foreign_pre_chain=shared_processors,
    )

    file_handler.setFormatter(file_formatter)
    console_handler.setFormatter(console_formatter)

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


def get_logger(name: str):
    """
    Get a logger with the given name.

    Args:
        name (str): The name of the logger.

    Returns:
        structlog.stdlib.BoundLogger: A structured logger.
    """
    return structlog.get_logger(name)


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