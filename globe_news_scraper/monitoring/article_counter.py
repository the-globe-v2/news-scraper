from typing import Dict
from urllib.parse import urlparse
from collections import defaultdict


class ArticleCounter:
    """
    A class to track the number of articles scraped from each provider and the total number of articles scraped.
    """

    def __init__(self) -> None:
        """
        Initialize the ArticleCounter with counters for total attempted articles and per-provider statistics.
        """
        self._total_attempted_articles = 0
        self._article_providers: Dict[str, Dict[str, int]] = defaultdict(lambda: {"failed": 0, "successful": 0})

    def track_build_attempt(self, url: str, success: bool) -> None:
        """
        Track an attempt to scrape an article, updating the total count and the count for the specific provider.

        :param url: The URL of the article that was attempted to be scraped.
        :param success: A boolean indicating whether the scraping attempt was successful.
        """
        self._total_attempted_articles += 1

        provider = urlparse(str(url)).netloc
        status = "successful" if success else "failed"
        self._article_providers[provider][status] += 1

    def get_total_attempted_articles(self) -> int:
        """
        Get the total number of article scraping attempts.

        :return: The total number of articles that have been attempted to be scraped.
        :rtype: int
        """
        return self._total_attempted_articles

    def get_all_provider_stats(self) -> Dict[str, Dict[str, int]]:
        """
        Get the statistics of article scraping attempts per provider.

        :return: A dictionary where the keys are provider domains and the values are dictionaries
                 with counts of successful and failed scraping attempts.
        :rtype: Dict[str, Dict[str, int]]
        """
        return self._article_providers
