import structlog
import requests
from requests.exceptions import SSLError, RequestException
from random import choice
from typing import Optional, Dict, cast

from playwright.sync_api import sync_playwright, Error as PlaywrightError

from globe_news_scraper.config import Config
from globe_news_scraper.monitoring.request_tracker import RequestTracker


class WebContentFetcher:
    def __init__(self, config: Config, request_tracker: RequestTracker) -> None:
        """
        Initialize the WebContentFetcher.

        Args:
            config (Config): Configuration object containing necessary settings.
        """
        self.logger = structlog.get_logger()
        self.user_agents = config.USER_AGENTS
        self.postman_ua = config.POSTMAN_USER_AGENT
        self.headers = config.HEADERS
        self.request_tracker = request_tracker

    def fetch_content(self, url: str) -> Optional[str]:
        """
        Fetch the content of a news webpage using various methods.

        This method attempts to fetch the content using requests, then with a Postman User-Agent,
        and finally with Playwright if the previous attempts fail.

        Args:
            url (str): The URL of the webpage to fetch.

        Returns:
            Optional[str]: The content of the webpage if successful, None otherwise.
        """
        # Set a random User-Agent header to avoid being blocked
        self.headers['User-Agent'] = choice(self.user_agents)

        # first try to fetch the page without JS rendering
        res = self._fetch_with_requests(url)
        status_code = cast(int, res['status'])
        if status_code == 200:
            self.request_tracker.track_request('basic_request', status_code)
            return cast(str, res['content'])

        # if the page is not fetched successfully, try to fetch it with Postman User-Agent (seems to help)
        else:
            # track the failed request
            self.request_tracker.track_request('basic_request', status_code)

            headers = self.headers
            headers['User-Agent'] = self.postman_ua
            res = self._fetch_with_requests(url, headers=headers)
            status_code = cast(int, res['status'])
            if status_code == 200:
                self.request_tracker.track_request('postman_request', status_code)
                return cast(str, res['content'])

            # if the page is still not fetched successfully, try to fetch it with Playwright
            else:
                # track the failed request
                self.request_tracker.track_request('postman_request', status_code)

                self.logger.debug(
                    f'HTTP {status_code}: Failed to fetch {url} with "requests" library. Trying Playwright.')
                res = self._fetch_with_playwright(url)
                status_code = cast(int, res['status'])
                if status_code == 200:
                    self.request_tracker.track_request('playwright_request', status_code)
                    return cast(str, res['content'])
                else:
                    # track the failed request
                    self.request_tracker.track_request('playwright_request', status_code)
                    self.logger.debug(f'HTTP {res['status']}: Playwright failed to load page: {url}')
                    return None

    def _fetch_with_requests(self, url: str, headers: Optional[Dict[str, str]] = None) -> Dict[str, str | int]:
        """
        Fetch the raw HTML content of a webpage using the "requests" library.

        Args:
            url (str): The URL of the webpage to fetch.
            headers (Optional[Dict[str, str]]): Custom headers to use for the request.

        Returns:
            Dict[str, str]: A dictionary containing the HTTP status code and the raw HTML content.
        """
        try:
            r = requests.get(url, headers=headers if headers else self.headers, timeout=10)

            # If the encoding is not apparent, return an empty string and pass on to playwright
            if not r.apparent_encoding:
                res: Dict[str, int | str] = {
                    'status': 500,
                    'content': ''
                }
            else:
                res = {
                    'status': r.status_code,
                    'content': r.text
                }
            return res
        except SSLError as e:
            # This catches SSL certificate verification errors
            self.logger.warning(f'SSL Certificate verification failed: {e}')
        except RequestException as e:
            # This catches other exceptions in the requests library, like connection errors
            self.logger.warning(f'HTTP request failed: {e}')
        except Exception as e:
            # This catches any other exceptions
            self.logger.warning(f'An unexpected error occurred: {e}')
        res = {
            'status': 500,
            'content': ''
        }
        return res

    def _fetch_with_playwright(self, url: str) -> Dict[str, str | int]:
        """
        Fetch the raw HTML content of a webpage using Playwright.

        Args:
            url (str): The URL of the webpage to fetch.

        Returns:
            Dict[str, str]: A dictionary containing the HTTP status code and the raw HTML content.
        """
        try:
            with (sync_playwright() as p):
                browser = p.firefox.launch()
                page = browser.new_page(extra_http_headers=self.headers)
                response = page.goto(url, timeout=10000)

                if response and response.status != 200:
                    browser.close()
                    res: Dict[str, int | str] = {
                        'status': response.status,
                        'content': ''
                    }
                    return res
                else:
                    raw_html = page.content()
                    browser.close()
                    res = {
                        'status': 200,
                        'content': raw_html
                    }
                    return res
        except PlaywrightError as e:
            self.logger.warning(f'Playwright error: {e}')
        except Exception as e:
            self.logger.warning(f'An unexpected error occurred: {e}')
        res = {
            'status': 500,
            'content': ''
        }
        return res

    def get_request_tracker(self) -> RequestTracker:
        """
        Get the RequestTracker object used by the WebContentFetcher.

        Returns:
            RequestTracker: The RequestTracker object.
        """
        return self.request_tracker
