# path: globe_news_scraper/monitoring/request_tracker.py

from collections import defaultdict
from typing import Dict, Tuple


class RequestTracker:
    """
    A class for tracking web requests to news sites and their success rates.
    Different news providers are tracked separately.
    """

    def __init__(self) -> None:
        """
        Initialize the RequestTracker with a dictionary to track requests by method and status code.
        """
        self._requests: Dict[str, Dict[int, int]] = defaultdict(lambda: {})

    def track_request(self, method: str, status_code: int) -> None:
        """
        Track a web request by incrementing the count for the given method and status code.

        :param method: The HTTP method used for the request (e.g., 'GET', 'POST').
        :param status_code: The HTTP status code returned from the request.
        """
        if status_code in self._requests[method].keys():
            self._requests[method][status_code] += 1
        else:
            self._requests[method][status_code] = 1

    def get_all_requests(self) -> Dict[str, Dict[int, int]]:
        """
        Retrieve all tracked requests with their respective status codes.

        :return: A dictionary where the keys are HTTP methods and the values are dictionaries
                 of status codes and their corresponding counts.
        :rtype: Dict[str, Dict[int, int]].
        """
        return self._requests

    def get_success_rate(self, method: str) -> float:
        """
        Calculate the success rate for a given HTTP method.

        :param method: The HTTP method to calculate the success rate for.
        :return: The success rate as a float, where 1.0 represents 100% success.
        :rtype: float
        """
        method_stats = self._requests[method]
        total = sum(count for count in method_stats.values())
        if 200 in method_stats:
            return method_stats[200] / total if total > 0 else 0.0
        else:
            return 0.0

    def get_all_success_rates(self) -> Dict[str, float]:
        """
        Get the success rates for all tracked HTTP methods.

        :return: A dictionary where the keys are HTTP methods and the values are their success rates as floats.
        :rtype: Dict[str, float]
        """
        return {method: self.get_success_rate(method) for method in self._requests}

    def get_total_requests(self) -> Tuple[int, int]:
        """
        Get the total number of successful and failed requests across all methods.

        :return: A tuple containing the total number of successful requests (status code 200)
                 and the total number of failed requests (any status code other than 200).
        :rtype: Tuple[int, int]
        """
        total_success = sum(stats[200] for stats in self._requests.values())
        total_failure = sum(
            sum(count for status_code, count in stats.items() if status_code != 200) for stats in
            self._requests.values())
        return total_success, total_failure
