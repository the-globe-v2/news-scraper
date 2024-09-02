import time
import argparse
import os
import structlog
from datetime import datetime
from croniter import croniter
from globe_news_scraper import GlobeNewsScraper
from globe_news_scraper.config import get_config
from globe_news_scraper.logger import configure_logging


def scrape_news(config):
    logger = structlog.get_logger()
    logger.info("Starting GlobeNewsScraper")

    try:
        scraper = GlobeNewsScraper(config)
        articles = scraper.scrape_daily()
    except Exception as e:
        logger.critical("Error while running GlobeNewsScraper: ", error=str(e))
        return

    # Log results
    scraper.telemetry.log_article_stats()
    scraper.telemetry.log_request_summary()
    scraper.telemetry.log_all_request_status_codes()

    logger.info(f"Fetched and stored {len(articles)} articles out of "
                f"{scraper.telemetry.article_counter.get_total_attempted_articles()} attempts")


def main():
    parser = argparse.ArgumentParser(description="GlobeNewsScraper")
    parser.add_argument('--env', type=str, choices=['dev', 'prod', 'test'],
                        help="Specify the environment (dev, prod or test)")
    parser.add_argument('--log-level', type=str, choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help="Set the logging level")
    parser.add_argument('--cron-schedule', type=str,
                        help="Set the cron schedule (e.g., '0 2 * * *' for daily at 2 AM)")
    parser.add_argument('--run-now', action='store_true',
                        help="Run the scraper immediately on startup")

    args = parser.parse_args()

    # Get configuration, prioritizing command-line arguments, then environment variables, then defaults
    config = get_config()

    # Override configuration with command-line arguments
    config.ENV = args.env or config.ENV
    config.LOG_LEVEL = args.log_level or config.LOG_LEVEL
    cron_schedule = args.cron_schedule or config.CRON_SCHEDULE
    run_now = args.run_now or config.RUN_ON_STARTUP

    # Configure logging
    configure_logging(log_level=config.LOG_LEVEL, logging_dir=config.LOGGING_DIR, environment=config.ENV)
    logger = structlog.get_logger()

    # Log the configuration
    logger.info("GlobeNewsScraper Configuration",
                env=config.ENV,
                log_level=config.LOG_LEVEL,
                cron_schedule=cron_schedule,
                run_now=run_now)

    # Run once immediately on startup if specified
    if run_now:
        logger.info("Running initial scrape")
        scrape_news(config)

    # Set up the cron iterator
    cron = croniter(cron_schedule, datetime.now())

    # Main loop
    while True:
        next_run = cron.get_next(datetime)
        logger.info(f"Next run scheduled for: {next_run}")

        while datetime.now() < next_run:
            time.sleep(60)

        logger.info("Starting scheduled scrape")
        scrape_news(config)


if __name__ == "__main__":
    main()