# path: main.py

import argparse
import structlog

from globe_news_scraper import GlobeNewsScraper
from globe_news_scraper.config import get_config
from globe_news_scraper.logger import configure_logging


def main():
    parser = argparse.ArgumentParser(description="GlobeNewsScraper")
    parser.add_argument('--env', type=str, choices=['dev', 'prod', 'test'], default='dev',
                        help="Specify the environment (dev, prod or test)")
    args = parser.parse_args()

    config = get_config()

    # Configure logging
    configure_logging(log_level=config.LOG_LEVEL, logging_dir=config.LOGGING_DIR, environment=args.env)
    logger = structlog.get_logger()

    logger.info(f"Starting GlobeNewsScraper in {args.env} mode")

    # Initialize and run the scraper
    try:
        scraper = GlobeNewsScraper(config)
        articles = scraper.scrape_daily()
    except Exception as e:
        logger.critical("Error while running GlobeNewsScraper: ", error=str(e))
        quit(1)

    # Log results
    scraper.telemetry.log_article_stats()
    scraper.telemetry.log_request_summary()
    scraper.telemetry.log_all_request_status_codes()

    logger.info(f"Fetched and stored {len(articles)} articles out of "
                f"{scraper.telemetry.article_counter.get_total_attempted_articles()} attempts")


if __name__ == "__main__":
    main()
