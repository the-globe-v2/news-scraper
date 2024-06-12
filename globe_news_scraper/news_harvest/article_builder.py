# Path: globe_news_scraper/news_harvest/globe_scraper.py
from typing import Optional

from globe_news_scraper.config import Config
from globe_news_scraper.models import GlobeArticle
from globe_news_scraper.news_harvest.news_crawler import Crawler
from goose_content_extractor import extract_content


class ArticleBuilder:
    def __init__(self, config: Config):
        self.news_crawler = Crawler(config)

    def build(self, url: str) -> GlobeArticle:
        raw_article = self.__fetch_raw_html(url)
        if raw_article:
            article = self.__extract_content(raw_article)
            return article
        else:
            raise BuildArticleError(f"Failed to build GlobeArticle object for {url}")

    def __fetch_raw_html(self, url: str) -> Optional[str]:
        return self.news_crawler.fetch_raw_html(url)

    def __extract_content(self, raw_html: str) -> Optional[GlobeArticle]:
        return raw_html


class BuildArticleError(Exception):
    pass
