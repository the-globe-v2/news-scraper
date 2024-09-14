# path: globe_news_scraper/logger.py

import os
import re
import logging
from logging import LogRecord
from logging.handlers import RotatingFileHandler
from typing import Literal

import structlog


class GooseWarningFilter(logging.Filter):
    """
    goose3 logs a warning when it can't resolve the publishing date to UTC.
    This filter removes that warning as GNS gets its pub timestamps from the NewsSources regardless.
    """

    def filter(self, record: LogRecord) -> bool:
        return not re.match(r'Publish date \d+ could not be resolved to UTC', record.getMessage())

class LLMGuardWarningFilter(logging.Filter):
    """
    llm-guard logs a warning when it detects invisible text.
    This filter removes that warning as GNS uses llm-guard to sanitize and remove that text.
    """

    def filter(self, record: LogRecord) -> bool:
        return not re.match(r'Found invisible characters in the prompt', record.getMessage())


def configure_logging(log_level: str, logging_dir: str = 'logs',
                      environment: Literal['dev', 'prod', 'test'] = 'dev') -> None:
    logger_level = logging.INFO if environment == 'prod' else getattr(logging, log_level.upper(), logging.INFO)

    # Ignore DEBUG messages from specific loggers
    for logger_name in ['urllib3', 'asyncio', 'goose3.crawler', 'pymongo', 'charset_normalizer', 'filelock']:
        logging.getLogger(logger_name).setLevel(logging.INFO)

    # Remove the warning about publish date not being resolved to UTC
    logging.getLogger('goose3.crawler').addFilter(GooseWarningFilter())

    # Remove the LLM Guard warning about invisible text
    logging.getLogger('llm_guard.input_scanners').addFilter(LLMGuardWarningFilter())

    # Ensure the logging directory exists
    log_dir = os.path.dirname(f'{logging_dir}/globe_news_scraper.log')
    os.makedirs(log_dir, exist_ok=True)

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
        wrapper_class=structlog.stdlib.BoundLogger,  # type: ignore[attr-defined]
        cache_logger_on_first_use=True,
    )

    # Set up formatter
    formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.dev.ConsoleRenderer() if environment == 'dev' else structlog.processors.JSONRenderer(),
    )

    # Add handler to the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logger_level)

    # Add StreamHandler
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)

    # Add FileHandler
    file_handler = RotatingFileHandler(
        f'{logging_dir}/globe_news_scraper.log',
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
