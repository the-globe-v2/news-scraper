# path: globe_news_scraper/monitoring/request_tracker.py

from collections import defaultdict
from typing import Dict, Tuple


class RequestTracker:
    """
    A class for tracking web requests to news sites and their success rates.
    Different news providers are tracked separately.
    """
    def __init__(self):
        self._requests: Dict[str, Dict[int, int]] = defaultdict(lambda: {})

    def track_request(self, method: str, status_code: int):
        if status_code in self._requests[method].keys():
            self._requests[method][status_code] += 1
        else:
            self._requests[method][status_code] = 1

    def get_all_requests(self) -> Dict[str, Dict[int, int]]:
        return self._requests

    def get_success_rate(self, method: str) -> float:
        method_stats = self._requests[method]
        total = sum(count for count in method_stats.values())
        return method_stats[200] / total if total > 0 else 0.0

    def get_all_success_rates(self) -> Dict[str, float]:
        return {method: self.get_success_rate(method) for method in self._requests}

    def get_total_requests(self) -> Tuple[int, int]:
        total_success = sum(stats[200] for stats in self._requests.values())
        total_failure = sum(
            sum(count for status_code, count in stats.items() if status_code != 200) for stats in
            self._requests.values())
        return total_success, total_failure
