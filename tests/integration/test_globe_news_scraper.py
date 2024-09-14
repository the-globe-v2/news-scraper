from datetime import datetime

import pytest
from pydantic_extra_types.country import CountryAlpha2
from pydantic_extra_types.language_code import LanguageAlpha2

from globe_news_scraper import GlobeNewsScraper
from globe_news_scraper.data_providers.news_sources.models import NewsSourceArticleData


@pytest.fixture
def mock_news_source(mocker, request):
    articles = (
        request.param
        if hasattr(request, "param")
        else [
            NewsSourceArticleData(
                title="Test article",
                url="https://example.com/test",
                description="This is a test article",
                date_published=datetime.now(),
                provider="Default Provider",
                origin_country=CountryAlpha2("GB"),
                language=LanguageAlpha2("en"),
                source_api="DefaultAPI",
            )
        ]
    )
    mock_source = mocker.Mock()
    mock_source.get_country_trending_news.return_value = articles
    mock_source.available_countries = ["en-GB"]
    return mock_source


@pytest.mark.integration
def test_scrape_daily(
        mock_config,
        mock_telemetry,
        mock_news_source,
        sample_news_article_html,
        mocker,
        log_output,
):
    mock_db_handler = mocker.Mock()
    mock_db_handler.does_article_exist.return_value = False
    mock_db_handler.insert_bulk_articles.return_value = (["test_id"], [])
    mocker.patch("globe_news_scraper.MongoHandler", return_value=mock_db_handler)
    mocker.patch(
        "globe_news_scraper.data_providers.news_sources.factory.NewsSourceFactory.get_all_sources",
        return_value=[mock_news_source],
    )
    mocker.patch(
        "globe_news_scraper.data_providers.news_pipeline.web_content_fetcher.WebContentFetcher.fetch_content",
        return_value=sample_news_article_html,
    )

    scraper = GlobeNewsScraper(mock_config)
    result = scraper.scrape_daily()

    assert len(result) == 1
    assert result[0] == "test_id"
    mock_news_source.get_country_trending_news.assert_called_once_with(mkt="en-GB")
    mock_db_handler.insert_bulk_articles.assert_called_once()
    assert log_output.entries == [
        {
            "event": "Successfully created GlobeArticle object for https://example.com/test",
            "log_level": "debug",
        },
        {
            "country": "en-GB",
            "total_trending_news": 1,
            "articles_built": 1,
            "articles_inserted": 1,
            "build_success_rate": "100.00%",
            "insert_success_rate": "100.00%",
            "event": "Country processing statistics",
            "log_level": "info",
        },
        {
            "news_source": "Mock",
            "country_code": "en-GB",
            "articles_count": 1,
            "event": "Country processing complete",
            "log_level": "info",
        },
    ]


@pytest.mark.integration
def test_scrape_daily_error_handling(
        mock_config, mock_telemetry, mock_news_source, mocker, log_output
):
    mock_db_handler = mocker.Mock()
    mock_db_handler.does_article_exist.return_value = False
    mock_db_handler.insert_bulk_articles.side_effect = Exception("Database error")
    mocker.patch("globe_news_scraper.MongoHandler", return_value=mock_db_handler)

    mocker.patch(
        "globe_news_scraper.data_providers.news_sources.factory.NewsSourceFactory.get_all_sources",
        return_value=[mock_news_source],
    )
    mocker.patch(
        "globe_news_scraper.data_providers.news_pipeline.web_content_fetcher.WebContentFetcher.fetch_content",
        return_value="<html><body>Test content</body></html>",
    )

    scraper = GlobeNewsScraper(mock_config)
    result = scraper.scrape_daily()

    assert len(result) == 0
    mock_news_source.get_country_trending_news.assert_called_once_with(mkt="en-GB")
    assert log_output.entries == [
        {
            "url": "https://example.com/test",
            "event": "Failed to extract article data with Goose extractor",
            "log_level": "warning",
        },
        {
            "country": "en-GB",
            "total_trending_news": 1,
            "articles_built": 0,
            "articles_inserted": 0,
            "build_success_rate": "0.00%",
            "insert_success_rate": "N/A",
            "event": "Country processing statistics",
            "log_level": "info",
        },
        {
            "news_source": "Mock",
            "country_code": "en-GB",
            "articles_count": 0,
            "event": "Country processing complete",
            "log_level": "info",
        },
    ]


@pytest.mark.integration
@pytest.mark.parametrize(
    "mock_news_source",
    [
        [
            NewsSourceArticleData(
                title="Test article 1",
                url="https://example.com/test1",
                description="This is a test article",
                date_published=datetime.now(),
                provider="Default Provider",
                origin_country=CountryAlpha2("GB"),
                language=LanguageAlpha2("en"),
                source_api="TestAPI",
                image_url="https://example.com/test_img.jpg",
            ),
            NewsSourceArticleData(
                title="Test article 2",
                url="https://example.com/test2",
                description="This is a test article",
                date_published=datetime.now(),
                provider="Default Provider",
                origin_country=CountryAlpha2("GB"),
                language=LanguageAlpha2("en"),
                source_api="TestAPI",
                image_url="https://example.com/test_img.jpg",
            ),
            NewsSourceArticleData(
                title="Test article 3",
                url="https://example.com/test3",
                description="This is a test article",
                date_published=datetime.now(),
                provider="Default Provider",
                origin_country=CountryAlpha2("GB"),
                language=LanguageAlpha2("en"),
                source_api="TestAPI",
                image_url="https://example.com/test_img.jpg",
            ),
        ]
    ],
    indirect=True,
)
def test_scrape_daily_partial_success(
        mock_config,
        mock_telemetry,
        mock_news_source,
        sample_news_article_html,
        sample_short_article_html,
        mocker,
        log_output,
):
    mock_db_handler = mocker.Mock()
    mock_db_handler.does_article_exist.side_effect = [False, True, False]
    mock_db_handler.insert_bulk_articles.return_value = (["test_id_1"], [])
    mocker.patch("globe_news_scraper.MongoHandler", return_value=mock_db_handler)
    mocker.patch(
        "globe_news_scraper.data_providers.news_sources.factory.NewsSourceFactory.get_all_sources",
        return_value=[mock_news_source],
    )

    def mock_fetch_content(url):
        if url == "https://example.com/test1":
            return sample_news_article_html
        elif url == "https://example.com/test3":
            return sample_short_article_html

    mocker.patch(
        "globe_news_scraper.data_providers.news_pipeline.web_content_fetcher.WebContentFetcher.fetch_content",
        side_effect=mock_fetch_content,
    )

    scraper = GlobeNewsScraper(mock_config)
    result = scraper.scrape_daily()

    assert len(result) == 1
    assert "test_id_1" == result[0]
    assert mock_news_source.get_country_trending_news.call_count == 1
    assert mock_db_handler.does_article_exist.call_count == 3
    assert mock_db_handler.insert_bulk_articles.call_count == 1
    assert {
               "event": "Article already exists in the database, skipping: "
                        "https://example.com/test2",
               "log_level": "debug",
           } in log_output.entries
    assert {
               "event": "Successfully created GlobeArticle object for "
                        "https://example.com/test1",
               "log_level": "debug",
           } in log_output.entries
    assert {
               "event": "Invalid content for https://example.com/test3: ['Content does not "
                        "meet minimum length of 100 characters']",
               "log_level": "debug",
           } in log_output.entries
    assert {
               "articles_built": 1,
               "articles_inserted": 1,
               "build_success_rate": "33.33%",
               "country": "en-GB",
               "event": "Country processing statistics",
               "insert_success_rate": "100.00%",
               "log_level": "info",
               "total_trending_news": 3,
           } in log_output.entries
