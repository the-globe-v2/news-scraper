# path: globe_news_scraper/database/db_init.py

import argparse
import structlog
import sys

from globe_news_scraper import Config
from globe_news_scraper.config import get_config
from globe_news_scraper.database.mongo_handler import MongoHandler, MongoHandlerError
from globe_news_scraper.logger import configure_logging

def setup_database(config: Config) -> None:
    """
    Set up the database by initializing it with the necessary collections to work within the Globe project.

    :param config: Configuration object
    :return: None
    """
    logger = structlog.get_logger()
    logger.info("Starting database initialization")

    try:
        mongo_handler = MongoHandler(config)
        mongo_handler.initialize_database()
        logger.info("Database initialization completed successfully")
    except MongoHandlerError as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error during database initialization: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize GlobeNewsScraper Database")
    parser.add_argument('--env', type=str, choices=['dev', 'prod', 'test'], default='dev',
                        help="Specify the environment (dev, prod or test)")
    args = parser.parse_args()

    config = get_config()

    # Override configuration with command-line arguments
    config.ENV = args.env

    # Configure logging
    configure_logging(log_level=config.LOG_LEVEL, logging_dir=config.LOGGING_DIR, environment=config.ENV)

    setup_database(config)