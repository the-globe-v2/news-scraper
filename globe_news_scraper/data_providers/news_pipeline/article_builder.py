# Path: globe_news_scraper/data_providers/globe_scraper.py
import datetime
from typing import Optional, Dict, Any
import structlog
from pycountry import languages
from pydantic import HttpUrl

from globe_news_scraper.data_providers.news_sources.models import NewsSourceArticleData
from globe_news_scraper.config import Config
from globe_news_scraper.monitoring import GlobeScraperTelemetry
from globe_news_scraper.models import GlobeArticle, ArticleData
from globe_news_scraper.data_providers.news_pipeline.content_validator import ContentValidator
from globe_news_scraper.data_providers.news_pipeline.web_content_fetcher import WebContentFetcher
from globe_news_scraper.data_providers.news_pipeline.article_extractor import extract_article


class ArticleBuilderError(Exception):
    """Base exception for ArticleBuilder errors"""


class ArticleBuilder:
    def __init__(self, config: Config, telemetry: GlobeScraperTelemetry):
        """
        Initialize the ArticleBuilder.

        Args:
            config (Config): Configuration object containing necessary settings.
            telemetry (GlobeScraperTelemetry): Telemetry object for tracking requests and articles. # should be optional
        """
        self._logger = structlog.get_logger()
        self._telemetry = telemetry
        self._web_content_fetcher = WebContentFetcher(config, self._telemetry.request_tracker)
        self._content_validator = ContentValidator(config)

    def build(self, news_item: NewsSourceArticleData) -> Optional[GlobeArticle]:
        """
        Build a GlobeArticle object from a news item.

        Args:
            news_item (dict): A dictionary containing metadata of a news article.

        Returns:
            Optional[GlobeArticle]: A GlobeArticle object if successfully built, None otherwise.
        """

        # Fetch the raw article content from a news_item URL
        raw_article = self._fetch_article_content(news_item.url)
        if not raw_article:
            self._telemetry.article_counter.track_scrape_attempt(news_item.url, success=False)
            self._logger.debug(f"No content to build GlobeArticle object with for {news_item.url}")
            return None

        # Build an ArticleData object from the raw article content
        try:
            article_data = self._extract_article_data(raw_article)
        except ArticleBuilderError as e:
            self._telemetry.article_counter.track_scrape_attempt(news_item.url, success=False)
            self._logger.warning("Failed to extract article data", error=str(e))
            return None

        # Sanitize the main article body content in the ArticleData
        article_data.cleaned_text = self._content_validator.sanitize(article_data.cleaned_text)

        # Validate content in the ArticleData
        article_is_valid, issues = self._content_validator.validate(article_data.cleaned_text)
        if not article_is_valid:
            self._telemetry.article_counter.track_scrape_attempt(news_item.url, success=False)
            self._logger.debug(f"Invalid content for {news_item.url}: {issues}")
            return None

        # Create a GlobeArticle object from the ArticleData and the data provided by the news api
        try:
            globe_article_object = self._create_globe_article(article_data, news_item)
            self._telemetry.article_counter.track_scrape_attempt(news_item.url, success=True)
            return globe_article_object
        except ArticleBuilderError as e:
            self._logger.warning(e)
            self._telemetry.article_counter.track_scrape_attempt(news_item.url, success=False)
            return None

    def _create_globe_article(self, extracted_data: ArticleData,
                              news_source_data: NewsSourceArticleData) -> GlobeArticle:
        """
        Create a GlobeArticle object from a ArticleData and the additional news source data provided by the news api.
        This method assumes reliable data from ArticleData and NewsSourceArticleData.

        Args:
            extracted_data (ArticleData): A ArticleData object containing extracted article content.
            news_source_data (NewsSourceArticleData): Additional data about the news article from the source api.

        Returns:
            GlobeArticle: A GlobeArticle object if successfully create.

        Raises:
            ArticleBuilderError: If the GlobeArticle object cannot be created.
        """


        try:
            built_globe_article = GlobeArticle(
                title=news_source_data.title,
                url=news_source_data.url,
                description=news_source_data.description,
                date_published=news_source_data.date_published,
                provider=news_source_data.provider,
                content=extracted_data.cleaned_text,
                keywords=[extracted_data.meta_keywords],
                authors=extracted_data.authors,
                origin_country=news_source_data.origin_country,
                image_url=news_source_data.image_url or extracted_data.top_image,
                date_scraped=datetime.datetime.today(),
                source_api=news_source_data.source_api,
                language=news_source_data.language or extracted_data.meta_lang
            )
            self._logger.debug(f"Successfully created GlobeArticle object for {news_source_data.url}")
            return built_globe_article

        except Exception as e:
            raise ArticleBuilderError(f"Failed to create GlobeArticle object for {news_source_data.url}: {e}")

    @staticmethod
    def _get_image_url(article_data: ArticleData) -> Optional[str]:
        """
        THIS METHOD DOES NOT WORK AND SHOULD BE FIXED
        Extract the image URL from a goose article.

        Args:
            article_data (ArticleData): An ArticleData object.

        Returns:
            Optional[str]: The URL of the top image if available, None otherwise.
        """
        top_image = getattr(article_data, 'top_image', None)
        return top_image.src if top_image else None

    def _fetch_article_content(self, url: str) -> Optional[str]:
        """
        Fetch the raw HTML content from the specified URL.

        Args:
            url (str): The URL of the webpage to fetch.

        Returns:
            Optional[str]: The raw HTML content as a string if successful, None if the fetch operation fails.
        """
        return self._web_content_fetcher.fetch_content(url)

    @staticmethod
    def _extract_article_data(raw_html: str) -> ArticleData:
        """
        When provided with a raw html string, uses Goose extractor to extract the article content.

        Args:
            raw_html (str): The raw HTML content of the article.

        Returns:
            ArticleData: A mutable version of the Goose Article object.
        """
        return extract_article(raw_html=raw_html)
