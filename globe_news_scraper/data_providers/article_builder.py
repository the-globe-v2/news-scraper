# Path: globe_news_scraper/data_providers/globe_scraper.py
import datetime
from typing import Optional, Dict, Any
import structlog

from globe_news_scraper.config import Config
from globe_news_scraper.models import GlobeArticle, MutableGooseArticle
from globe_news_scraper.data_providers.web_content_fetcher import WebContentFetcher
from globe_news_scraper.data_providers.goose_content_extractor import extract_content


class ArticleBuilderError(Exception):
    """Base exception for ArticleBuilder errors"""


class ArticleBuilder:
    def __init__(self, config: Config):
        """
        Initialize the ArticleBuilder.

        Args:
            config (Config): Configuration object containing necessary settings.
        """
        self.web_content_fetcher = WebContentFetcher(config)
        self.logger = structlog.get_logger()

    def build(self, news_item) -> Optional[GlobeArticle]:
        """
        Build a GlobeArticle object from a news item.

        Args:
            news_item (dict): A dictionary containing metadata of a news article.

        Returns:
            Optional[GlobeArticle]: A GlobeArticle object if successfully built, None otherwise.
        """
        raw_article = self._fetch_article_content(news_item['url'])
        if not raw_article:
            self.logger.debug(f"No content to build GlobeArticle object with for {news_item['url']}")
            return None

        goose_article = self._create_goose_article(raw_article)
        if not goose_article or len(goose_article.cleaned_text) < 300:  # arbitrary minimum content length
            self.logger.debug(f"Insufficient content length for {news_item['url']}")
            return None

        return self._create_globe_article(goose_article, news_item)

    def _create_globe_article(self, goose_article: MutableGooseArticle, news_source_data: Dict[str, Any]) -> Optional[
        GlobeArticle]:
        """
        Create a GlobeArticle object from a MutableGooseArticle
        and the additional news source data provided by the news api.

        Args:
            goose_article (MutableGooseArticle): A MutableGooseArticle object containing extracted article content.
            news_source_data (Dict[str, Any]): Additional data about the news article from the source api.

        Returns:
            Optional[GlobeArticle]: A GlobeArticle object if successfully created, None otherwise.
        """
        try:
            return GlobeArticle(
                title=news_source_data.get('title', getattr(goose_article, 'title', '')),
                url=news_source_data.get('url', ''),
                description=news_source_data.get('description', getattr(goose_article, 'description', '')),
                date_published=news_source_data.get('date_published', getattr(goose_article, 'publish_date', '')),
                provider=news_source_data.get('provider', ''),
                language=getattr(goose_article, 'meta_lang', ''),
                content=getattr(goose_article, 'cleaned_text', ''),
                # add the search query as a keyword
                keywords=getattr(goose_article, 'tags', []) + [news_source_data.get('query', '')],
                category=news_source_data.get('category', ''),
                authors=getattr(goose_article, 'authors', []),
                summary=getattr(goose_article, 'meta_description', ''),
                geographic_origin=getattr(goose_article, 'geographic_origin', None),
                image_url=news_source_data.get('img_url', self._get_image_url(goose_article)),
                is_breaking_news=news_source_data.get('is_breaking_news', False),
                trending_date=datetime.datetime.today()
            )
        except Exception as e:
            self.logger.warning(f"Failed to create GlobeArticle object for {news_source_data['url']}: {e}")
            return None

    @staticmethod
    def _get_image_url(goose_article) -> Optional[str]:
        """
        Extract the image URL from a goose article. Still WIP.

        Args:
            goose_article (MutableGooseArticle): A MutableGooseArticle object.

        Returns:
            Optional[str]: The URL of the top image if available, None otherwise.
        """
        top_image = getattr(goose_article, 'top_image', None)
        return top_image.src if top_image else None

    def _fetch_article_content(self, url: str) -> Optional[str]:
        """
        Fetch the raw HTML content from the specified URL.

        Args:
            url (str): The URL of the webpage to fetch.

        Returns:
            Optional[str]: The raw HTML content as a string if successful, None if the fetch operation fails.
        """
        return self.web_content_fetcher.fetch_content(url)

    @staticmethod
    def _create_goose_article(raw_html: str) -> MutableGooseArticle:
        """
        When provided with a raw html string, uses Goose extractor to extract the article content.

        Args:
            raw_html (str): The raw HTML content of the article.

        Returns:
            MutableGooseArticle: A mutable version of the Goose Article object.
        """
        return extract_content(raw_html=raw_html)
