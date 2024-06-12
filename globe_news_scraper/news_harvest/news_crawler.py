# path: globe_news_scraper/news_harvest/news_crawler.py

import structlog
import requests
from requests.exceptions import SSLError, RequestException

from typing import Optional, Dict

from playwright.sync_api import sync_playwright
from playwright._impl._errors import Error as PlaywrightError

from globe_news_scraper.config import Config


class Crawler:
    """
    A class to fetch the raw HTML content of a webpage. It uses the requests library to fetch the page without JS
    rendering. If the page is not fetched successfully, it uses Playwright to fetch the page with JS rendering.

    params: config (Config): The configuration object.
    """
    def __init__(self, config: Config) -> None:
        self.logger = structlog.get_logger()
        self.user_agent = config.USER_AGENTS[0]
        self.headers = config.HEADERS
        if self.user_agent:
            self.headers["User-Agent"] = self.user_agent

    def fetch_raw_html(self, url: str) -> Optional[str]:
        # first try to fetch the page without JS rendering
        res = self.__fetch_no_js(url)
        if res["status"] == 200:
            return res["content"]
        else:
            self.logger.debug(f"Failed to fetch {url} with requests. Trying Playwright.")
            # if there are any issues, try to fetch the page with JS rendering
            res = self.__fetch_advanced(url)
            if res["status"] == 200:
                return res["content"]
            else:
                self.logger.debug(f"Failed to fetch {url} with Playwright.")
                return None

    def __fetch_no_js(self, url: str) -> Dict[str, str]:
        """
        Fetches the raw HTML content of a webpage using requests.

        :param url (str): The URL of the webpage to fetch.
        :return: (Dict[str, int | str]) A dictionary containing the HTTP status code and the raw HTML content.
        """
        try:
            r = requests.get(url, headers=self.headers)
            res: Dict[str, int | str] = {
                "status": r.status_code,
                "content": r.text
            }
            return res
        except SSLError as e:
            # This catches SSL certificate verification errors
            self.logger.warning(f"SSL Certificate verification failed: {e}")
        except RequestException as e:
            # This catches other exceptions in the requests library, like connection errors
            self.logger.warning(f"HTTP request failed: {e}")
        except Exception as e:
            # This catches any other exceptions
            self.logger.warning(f"An unexpected error occurred: {e}")
        res: Dict[str, int | str] = {
            "status": 500,
            "content": ""
        }
        return res

    def __fetch_advanced(
            self,
            url: str,
    ) -> Dict[str, int | str | None]:
        """
        Fetches the raw HTML content of a webpage using Playwright.

        :param url (str): The URL of the webpage to fetch.
        :return: (Dict[str, int | str | None])A dictionary containing the HTTP status code and the raw HTML content.
        """
        try:
            with (sync_playwright() as p):
                browser = p.firefox.launch()
                page = browser.new_page(extra_http_headers=self.headers)
                response = page.goto(url)

                if response and response.status != 200:
                    self.logger.debug(f"HTTP {response.status}: Playwright failed to load page: {url}")
                    browser.close()
                    res: Dict[str, int | str | None] = {
                        "status": response.status,
                        "content": None
                    }
                    return res
                else:
                    raw_html = page.content()
                    browser.close()
                    res: Dict[str, int | str | None] = {
                        "status": 200,
                        "content": raw_html
                    }
                    return res
        except PlaywrightError as e:
            self.logger.warning(f"Playwright error: {e}")
        except Exception as e:
            self.logger.warning(f"An unexpected error occurred: {e}")
        res: Dict[str, int | str | None] = {
            "status": 500,
            "content": None
        }
        return res
