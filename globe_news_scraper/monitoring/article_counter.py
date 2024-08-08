from typing import Dict
from urllib.parse import urlparse
from collections import defaultdict


class ArticleCounter:
    """
    A class to track the number of articles scraped from each provider and the total number of articles scraped.
    """
    def __init__(self):
        self._total_attempted_articles = 0
        self._article_providers = defaultdict(lambda: {"failed": 0, "successful": 0})

    def track_scrape_attempt(self, url: str, success: bool):
        self._total_attempted_articles += 1

        provider = urlparse(url).netloc
        status = "successful" if success else "failed"
        self._article_providers[provider][status] += 1

    def get_total_attempted_articles(self) -> int:
        return self._total_attempted_articles

    def get_all_provider_stats(self) -> Dict[str, Dict[str, int]]:
        return self._article_providers
