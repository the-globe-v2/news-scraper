# path: globe_news_scraper/data_providers/news_pipeline/web_content_fetcher.py

import time
from random import choice
from typing import Optional, Dict, Callable, Tuple, cast
from urllib.parse import urlparse

import requests
import structlog
from playwright.sync_api import sync_playwright, TimeoutError, Error as PlaywrightError

from globe_news_scraper.config import Config
from globe_news_scraper.monitoring.request_tracker import RequestTracker


class WebContentFetcher:
    """
    A class for fetching the content of web pages using various methods, including requests, custom fetchers,
    and Playwright for more complex pages.
    """

    def __init__(self, config: Config, request_tracker: RequestTracker) -> None:
        """
        Initialize the WebContentFetcher.

        :param config: Configuration object containing necessary settings.
        :param request_tracker: Request tracker for monitoring fetch attempts.
        """
        self._logger = structlog.get_logger()
        self._user_agents = config.USER_AGENTS
        self._postman_ua = config.POSTMAN_USER_AGENT
        self._headers = config.HEADERS
        self._request_tracker = request_tracker
        self._domain_fetchers: Dict[str, Callable[[str], Tuple[int, str]]] = self._initialize_domain_fetchers()

    def _initialize_domain_fetchers(self) -> Dict[str, Callable[[str], Tuple[int, str]]]:
        """
        Initialize the dictionary of domain-specific fetchers.

        :return: A dictionary of domain names and their corresponding custom fetcher functions.
        """
        return {
            "www.msn.com": self._fetch_msn_com,
        }

    def fetch_content(self, url: str) -> Optional[str]:
        """
        Fetch the content of a news webpage using various methods.

        This method first checks if there's a custom fetcher for the domain, then attempts to fetch the content
        using requests, then with a Postman User-Agent, and finally with Playwright if the previous attempts fail.

        :param url: The URL of the webpage to fetch.
        :return: The content of the webpage if successful, None otherwise.
        """
        domain = urlparse(url).netloc

        # Check if there is a custom fetcher for the domain
        if domain in self._domain_fetchers:
            response_status, response_content = self._domain_fetchers[domain](url)
            if response_status == 200:
                self._request_tracker.track_request(f'custom_{domain}_request', 200)
                return response_content
            else:
                self._request_tracker.track_request(f'custom_{domain}_request', response_status)
                return None  # Other methods are unlikely to work if the custom one fails

        # Set a random User-Agent header to avoid being blocked
        self._headers['User-Agent'] = choice(self._user_agents)

        # Attempt to fetch with requests
        response_status, response_content = self._fetch_with_requests(url)
        if response_status == 200:
            self._request_tracker.track_request('basic_request', 200)
            return cast(str, response_content)

        # Attempt to fetch with Postman User-Agent
        headers = self._headers.copy()
        headers['User-Agent'] = self._postman_ua
        response_status, response_content = self._fetch_with_requests(url, headers=headers)
        if response_status == 200:
            self._request_tracker.track_request('postman_request', 200)
            return cast(str, response_content)

        # Attempt to fetch with Playwright
        self._logger.debug(f'Failed to fetch {url} with "requests" library. Trying Playwright.')
        response_status, response_content = self._fetch_with_playwright(url)
        if response_status == 200:
            self._request_tracker.track_request('playwright_request', 200)
            return cast(str, response_content)

        self._request_tracker.track_request('all_methods_failed', response_status)
        self._logger.debug(f'All methods failed to load page: {url}')
        return None

    def _fetch_with_requests(self, url: str, headers: Optional[Dict[str, str]] = None) -> Tuple[int, str]:
        """
        Fetch the raw HTML content of a webpage using the "requests" library.

        :param url: The URL of the webpage to fetch.
        :param headers: Optional custom headers to use for the request.
        :return: A tuple containing the HTTP status code and the raw HTML content.
        """
        try:
            r = requests.get(url, headers=headers if headers else self._headers, timeout=10)

            # If the encoding is not apparent, return an empty string and pass on to Playwright
            if not r.apparent_encoding:
                return 500, ''
            r.encoding = r.apparent_encoding
            return r.status_code, r.text
        except Exception as e:
            self._logger.warning(f'Request failed for {url}: {str(e)}')
            return 500, ''

    def _fetch_with_playwright(self, url: str) -> Tuple[int, str]:
        """
        Fetch the raw HTML content of a webpage using Playwright.

        :param url: The URL of the webpage to fetch.
        :return: A tuple containing the HTTP status code and the raw HTML content.
        """
        try:
            with sync_playwright() as p:
                browser = p.firefox.launch()
                page = browser.new_page(extra_http_headers=self._headers)
                response = page.goto(url, timeout=10000)

                if response and response.status != 200:
                    browser.close()
                    return response.status, ''
                else:
                    raw_html = page.content()
                    browser.close()
                    return 200, raw_html
        except (PlaywrightError, Exception) as e:
            self._logger.warning(f'Playwright error for {url}: {str(e)}')
            return 500, ''

    def _fetch_msn_com(self, url: str) -> Tuple[int, str]:
        """
        Custom fetcher for msn.com articles that extracts the full content and returns it within the complete HTML structure.

        This version waits for specific selectors to be visible, extracts the relevant content,
        and then returns the full HTML including the extracted article content.

        :param url: The URL of the MSN article to fetch.
        :return: A tuple containing the HTTP status code and the full HTML content.
        """
        with sync_playwright() as p:
            browser = p.firefox.launch(headless=True)
            context = browser.new_context(ignore_https_errors=False)
            page = context.new_page()

            try:
                page.goto(url, timeout=10000)

                # Define selectors to wait for
                selectors = [
                    "[id^='ViewsPageId-']",
                    "msn-article-page",
                    ".article-page",
                    "cp-article-reader"
                ]

                # Wait for any of the selectors to be visible
                for selector in selectors:
                    try:
                        page.wait_for_selector(selector, state="visible", timeout=10000)
                        break
                    except PlaywrightError:
                        continue
                else:
                    self._logger.warning(f"MSN Fetcher - No selectors found within the timeout period for: {url}")

                # Additional wait to allow dynamic content to load
                time.sleep(5)

                # Extract the content and full HTML
                full_html_with_content = page.evaluate('''() => {
                    function getOuterHTML(element) {
                        return element ? element.outerHTML : null;
                    }

                    // Try multiple methods to find the article content
                    const methods = [
                        () => {
                            const cpArticle = document.querySelector("cp-article");
                            return cpArticle && cpArticle.shadowRoot ? 
                                cpArticle.shadowRoot.querySelector(".article-body") : null;
                        },
                        () => document.querySelector(".article-body"),
                        () => document.querySelector("article"),
                        () => document.querySelector("[id^='ViewsPageId-']"),
                        () => document.body  // Last resort
                    ];

                    let contentElement = null;
                    for (const method of methods) {
                        contentElement = method();
                        if (contentElement) break;
                    }

                    if (!contentElement) {
                        return document.documentElement.outerHTML;
                    }

                    // Extract the content
                    const extractedContent = contentElement.innerHTML;

                    // Insert the extracted content back into the document
                    const articleBodyPlaceholder = document.querySelector('cp-article');
                    if (articleBodyPlaceholder) {
                        articleBodyPlaceholder.innerHTML = extractedContent;
                    }

                    // Return the full HTML including the extracted content
                    return document.documentElement.outerHTML;
                }''')

                return 200, full_html_with_content
            except TimeoutError:
                self._logger.warning(f"Failed to fetch article from MSN: Timeout exceeded for {url}")
                return 408, ''
            except Exception as e:
                self._logger.warning(f"MSN - Failed to fetch article content for {url}: {str(e)}")
                return 500, ''
            finally:
                context.close()
                browser.close()

    @property
    def request_tracker(self) -> RequestTracker:
        """
        Get the RequestTracker object used by the WebContentFetcher.

        :return: The RequestTracker object.
        """
        return self._request_tracker
