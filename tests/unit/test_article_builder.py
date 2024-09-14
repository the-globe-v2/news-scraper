# path: tests/unit/test_article_builder.py

from datetime import datetime

import pytest

from globe_news_scraper.data_providers.news_pipeline.article_builder import (
    ArticleBuilder,
)
from globe_news_scraper.data_providers.news_sources.models import NewsSourceArticleData
from globe_news_scraper.models import ArticleData


@pytest.mark.unit
def test_build_article(mock_config, mock_telemetry, log_output):
    builder = ArticleBuilder(mock_config, mock_telemetry)

    news_item = NewsSourceArticleData(
        title="Test Article",
        url="https://example.com/test",
        description="This is a test article",
        date_published=datetime.now(),
        provider="Test Provider",
        origin_country="DE",
        language="de",
        source_api="TestAPI",
    )

    # Mock the fetch_article_content and extract_article_data methods
    builder._fetch_article_content = (
        lambda
            url: "<html><body>This is a test content for the article, and it's made longer to satisfy the character limit requirement. The purpose is to extend the content to more than 100 characters for testing.</body></html>"
    )

    builder._extract_article_data = lambda raw_html: ArticleData(
        cleaned_text="This is a test content for the article, and it's made longer to satisfy the character limit requirement. The purpose is to extend the content to more than 100 characters for testing.",
        meta_lang="es",
        meta_keywords="test, article",
        authors=["Test Author"],
        top_image="https://www.bing.com/th?id=OVFT.KU1gWyrE_N2AVOMPy5flJy",
    )

    article = builder.build(news_item)

    assert article is not None
    assert article.title == "Test Article"
    assert article.url == "https://example.com/test"
    assert len(article.content) == 187
    assert article.origin_country == "DE"
    assert article.language == "de"
    assert {
               'event': 'Successfully created GlobeArticle object for https://example.com/test',
               'log_level': 'debug'
           } in log_output.entries


def test_build_article_content_too_short(mock_config, mock_telemetry, log_output):
    builder = ArticleBuilder(mock_config, mock_telemetry)

    news_item = NewsSourceArticleData(
        title="Test Article",
        url="https://example.com/test",
        description="This is a test article",
        date_published=datetime.now(),
        provider="Test Provider",
        origin_country="DE",
        language="de",
        source_api="TestAPI",
    )

    # Mock successful content fetching and extraction
    builder._fetch_article_content = lambda url: "<html><body>Test content</body></html>"
    builder._extract_article_data = lambda raw_html: ArticleData(
        cleaned_text="Test content",
        meta_lang="en",
        meta_keywords="test, article",
        authors=["Test Author"],
        top_image=None
    )

    article = builder.build(news_item)

    assert article is None
    assert {
               'event': "Invalid content for https://example.com/test: ['Content does not meet minimum length of 100 characters']",
               'log_level': 'debug'
           } in log_output.entries


@pytest.mark.unit
def test_build_article_no_content(mock_config, mock_telemetry, log_output):
    builder = ArticleBuilder(mock_config, mock_telemetry)

    news_item = NewsSourceArticleData(
        title="Test Article",
        url="https://example.com/test",
        description="This is a test article",
        date_published=datetime.now(),
        provider="Test Provider",
        origin_country="DE",
        language="de",
        source_api="TestAPI",
    )

    # Mock a failure in fetching content
    builder._fetch_article_content = lambda url: None

    article = builder.build(news_item)

    assert article is None
    assert {
               'event': 'No content to build GlobeArticle object with for https://example.com/test',
               'log_level': 'debug'
           } in log_output.entries
