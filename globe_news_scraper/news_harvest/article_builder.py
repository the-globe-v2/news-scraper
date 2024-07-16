# Path: globe_news_scraper/news_harvest/globe_scraper.py
from typing import Optional, Tuple, List

from globe_news_scraper.config import Config
from globe_news_scraper.models import GlobeArticle, GooseArticleClone
from globe_news_scraper.news_harvest.news_crawler import Crawler
from globe_news_scraper.news_harvest.goose_content_extractor import extract_content


class ArticleBuilder:
    def __init__(self, config: Config):
        self.news_crawler = Crawler(config)

    def build(self, url: str) -> GlobeArticle:
        raw_article = self.__fetch_raw_html(url)
        if raw_article:
            article = self.__extract_content(raw_article)
            return article
        else:
            raise BuildArticleError("No content to build GlobeArticle object with.")

    def __fetch_raw_html(self, url: str) -> Optional[str]:
        """
        Fetches the raw HTML content from the specified URL.

        Args:
            url (str): The URL of the webpage to fetch.

        Returns:
            Optional[str]: The raw HTML content as a string if successful,
                           or None if the fetch operation fails.

        Raises:
            Any exceptions raised by self.news_crawler() method.
        """
        return self.news_crawler.fetch_raw_html(url)

    def __extract_content(self, raw_html: str) -> GooseArticleClone:
        """When provided with a raw html string, uses goose and """
        goose_content = extract_content(raw_html=raw_html)

        return goose_content


class BuildArticleError(Exception):
    pass
