from datetime import datetime

import pytest

from globe_news_scraper.data_providers.news_pipeline import NewsPipeline
from globe_news_scraper.data_providers.news_sources.models import NewsSourceArticleData
from globe_news_scraper.models import GlobeArticle


@pytest.fixture
def mock_news_source(mocker):
    mock_source = mocker.Mock()
    mock_source.get_country_trending_news.return_value = [
        NewsSourceArticleData(
            title="Test Article",
            url="https://example.com/test",
            description="This is a test article",
            date_published=datetime.now(),
            provider="Test Provider",
            origin_country="DE",
            language="de",
            source_api="TestAPI"
        )
    ]
    mock_source.available_countries = ["DE"]
    return mock_source


@pytest.fixture
def mock_article_builder(mocker):
    mock_builder = mocker.Mock()
    mock_builder.build.return_value = GlobeArticle(
        title="Test Article",
        url="https://example.com/test",
        description="This is a test article",
        date_published=datetime.now(),
        provider="Test Provider",
        language="de",
        content="Test content",
        origin_country="DE",
        source_api="TestAPI"
    )
    return mock_builder


@pytest.mark.integration
def test_run_pipeline(mock_config, mock_telemetry, mock_news_source, mock_article_builder, mocker, log_output):
    mock_db_handler = mocker.Mock()
    mock_db_handler.does_article_exist.return_value = False
    mock_db_handler.insert_bulk_articles.return_value = (["test_id"], [])

    mocker.patch('globe_news_scraper.data_providers.news_pipeline.NewsSourceFactory.get_all_sources',
                 return_value=[mock_news_source])
    mocker.patch('globe_news_scraper.data_providers.news_pipeline.ArticleBuilder', return_value=mock_article_builder)

    pipeline = NewsPipeline(mock_config, mock_db_handler, mock_telemetry)
    result = pipeline.run_pipeline()

    assert len(result) == 1
    assert result[0] == "test_id"
    mock_news_source.get_country_trending_news.assert_called_once_with(mkt="DE")
    mock_article_builder.build.assert_called_once()
    mock_db_handler.insert_bulk_articles.assert_called_once()
    assert {'articles_built': 1,
            'articles_inserted': 1,
            'build_success_rate': '100.00%',
            'country': 'DE',
            'event': 'Country processing statistics',
            'insert_success_rate': '100.00%',
            'log_level': 'info',
            'total_trending_news': 1} in log_output.entries
    assert 'error' not in set(key for d in log_output.entries for key in d.keys())


@pytest.mark.integration
def test_run_pipeline_existing_article(mock_config, mock_telemetry, mock_news_source, mock_article_builder, mocker,
                                       log_output):
    mock_db_handler = mocker.Mock()
    mock_db_handler.does_article_exist.return_value = True

    mocker.patch('globe_news_scraper.data_providers.news_pipeline.NewsSourceFactory.get_all_sources',
                 return_value=[mock_news_source])
    mocker.patch('globe_news_scraper.data_providers.news_pipeline.ArticleBuilder', return_value=mock_article_builder)

    pipeline = NewsPipeline(mock_config, mock_db_handler, mock_telemetry)
    result = pipeline.run_pipeline()

    assert len(result) == 0
    mock_news_source.get_country_trending_news.assert_called_once_with(mkt="DE")
    mock_article_builder.build.assert_not_called()
    mock_db_handler.insert_bulk_articles.assert_not_called()
    assert {'articles_built': 0,
            'articles_inserted': 0,
            'build_success_rate': '0.00%',
            'country': 'DE',
            'event': 'Country processing statistics',
            'insert_success_rate': 'N/A',
            'log_level': 'info',
            'total_trending_news': 1} in log_output.entries
    assert 'error' not in set(key for d in log_output.entries for key in d.keys())


@pytest.mark.integration
def test_run_pipeline_error_handling(mock_config, mock_telemetry, mock_news_source, mock_article_builder, mocker,
                                     log_output):
    mock_db_handler = mocker.Mock()
    mock_db_handler.does_article_exist.return_value = False
    mock_db_handler.insert_bulk_articles.side_effect = Exception("Database error")

    mocker.patch('globe_news_scraper.data_providers.news_pipeline.NewsSourceFactory.get_all_sources',
                 return_value=[mock_news_source])
    mocker.patch('globe_news_scraper.data_providers.news_pipeline.ArticleBuilder', return_value=mock_article_builder)

    pipeline = NewsPipeline(mock_config, mock_db_handler, mock_telemetry)
    result = pipeline.run_pipeline()

    assert len(result) == 0
    mock_news_source.get_country_trending_news.assert_called_once_with(mkt="DE")
    mock_article_builder.build.assert_called_once()
    mock_db_handler.insert_bulk_articles.assert_called_once()
    assert {'error': 'Database error', 'event': 'Bulk insert failed', 'log_level': 'error'} in log_output.entries
