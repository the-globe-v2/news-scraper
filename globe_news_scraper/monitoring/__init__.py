import structlog
from typing import Dict
from collections import defaultdict

from globe_news_scraper.monitoring.request_tracker import RequestTracker
from globe_news_scraper.monitoring.article_counter import ArticleCounter


class GlobeScraperTelemetry:
    """
    A class for logging and tracking telemetry data for the GlobeNewsScraper.
    It counts the success rate of fully building a GlobeArticle object from a news item
    and tracks the success rate of web requests to news sites.
    Performance metrics and more detailed analytics are a potential future addition.
    """

    def __init__(self) -> None:
        """
        Initialize the GlobeScraperTelemetry with a logger, request tracker, and article counter.
        """
        self._logger = structlog.get_logger()
        self._request_tracker = RequestTracker()
        self._article_counter = ArticleCounter()

    @property
    def request_tracker(self) -> RequestTracker:
        """
        Get the request tracker instance.

        :return: The RequestTracker instance used for tracking web request statistics.
        """
        return self._request_tracker

    @property
    def article_counter(self) -> ArticleCounter:
        """
        Get the article counter instance.

        :return: The ArticleCounter instance used for tracking article scraping statistics.
        """
        return self._article_counter

    def log_request_summary(self) -> None:
        """
        Log a summary of all web requests tracked, including success and failure counts, and success rates.
        """
        for method, stats in self._request_tracker.get_all_requests().items():
            success_rate = self._request_tracker.get_success_rate(method)
            self._logger.info(f"{method} request stats",
                              success_count=stats[200],
                              failure_count=sum(count for status_code, count in stats.items() if status_code != 200),
                              success_rate=f"{success_rate:.2%}")

    def log_all_request_status_codes(self) -> None:
        """
        Log a detailed breakdown of HTTP status codes for all methods, as well as overall status code distribution.
        """
        all_request_stats = self._request_tracker.get_all_requests()
        self._logger.info("Detailed status code breakdown for all methods: ")
        for method, stats in all_request_stats.items():
            total_requests = sum(stats.values())
            status_code_percentages = {
                str(status_code): f"{count / total_requests:.2%}"
                for status_code, count in stats.items()
            }
            self._logger.info(f"{method} status code breakdown",
                              total_requests=total_requests,
                              **status_code_percentages)

        # Log overall status code distribution
        all_stats: Dict[int, int] = defaultdict(int)
        for stats in all_request_stats.values():
            for status_code, count in stats.items():
                all_stats[status_code] += count
        total_overall = sum(all_stats.values())
        overall_percentages = {
            str(status_code): f"{count / total_overall:.2%}"
            for status_code, count in all_stats.items()
        }
        self._logger.info("Overall status code distribution",
                          total_requests=total_overall,
                          **overall_percentages)

    def log_article_stats(self) -> None:
        """
        Log statistics about the articles scraped, including total attempted articles and stats per provider.
        """
        total_articles = self._article_counter.get_total_attempted_articles()
        provider_stats = self._article_counter.get_all_provider_stats()
        self._logger.info("Article scraping stats",
                          total_articles=total_articles,
                          provider_stats=provider_stats)
