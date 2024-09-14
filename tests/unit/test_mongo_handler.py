from datetime import datetime, timezone

import pytest
from pymongo.errors import PyMongoError, OperationFailure, ExecutionTimeout, BulkWriteError

from globe_news_scraper.database.mongo_handler import MongoHandler, MongoHandlerError
from globe_news_scraper.models import GlobeArticle


@pytest.fixture
def mock_mongo_client(mocker):
    mock_client = mocker.patch('pymongo.MongoClient')
    mock_db = mocker.MagicMock()
    mock_collection = mocker.MagicMock()
    mock_client.return_value.__getitem__.return_value = mock_db
    mock_db.__getitem__.return_value = mock_collection
    mock_db.list_collection_names.return_value = ['articles']
    mock_client.return_value.list_database_names.return_value = ['test_db']
    return mock_client.return_value


@pytest.fixture
def mongo_handler(mock_config, mock_mongo_client):
    return MongoHandler(mock_config, client=mock_mongo_client)


@pytest.mark.slow
def test_init_failure(mock_config, mocker):
    mocker.patch('pymongo.MongoClient', side_effect=PyMongoError("Connection failed"))
    with pytest.raises(MongoHandlerError):
        MongoHandler(mock_config)


@pytest.mark.unit
def test_init_success(mongo_handler, mock_mongo_client):
    assert (
            mongo_handler._db.name == mock_mongo_client[mongo_handler._config.MONGO_DB].name
    )
    assert "articles" in mongo_handler._db.list_collection_names()


@pytest.mark.unit
def test_initialize_database(mongo_handler):
    mongo_handler.initialize_database()
    # Check if indexes are created
    assert mongo_handler._articles.create_index.call_count == 7  # +1 call in _check_permissions
    assert (
            mongo_handler._db.command.call_count == 4
    )  # Two view creations and one schema validation +1 call in _check_permissions


@pytest.mark.unit
def test_insert_bulk_articles_success(mongo_handler):
    mongo_handler._articles.insert_many.return_value.inserted_ids = ["id1", "id2"]

    articles = [
        GlobeArticle(
            title="Prueba Artículo 1",
            title_translated=None,
            url="https://example.com/1",
            description="Descripción de prueba 1",
            description_translated=None,
            date_published=datetime.now(timezone.utc),
            provider="Test Provider",
            language="es",
            content="Contenido de Prueba 1",
            origin_country="ES",
            keywords=["test", "article", "example"],
            source_api="TestAPI",
            category=None,
            authors=["John Doe", "Jane Smith"],
            related_countries=[],
            image_url="https://example.com/image1.jpg",
            post_processed=False,
        ),
        GlobeArticle(
            title="Test Artikel 2",
            title_translated=None,
            url="https://example.com/2",
            description="Test Beschreibung 2",
            description_translated=None,
            date_published=datetime.now(timezone.utc),
            provider="Test Provider",
            language="de",
            content="Test Inhalte 2",
            origin_country="DE",
            keywords=["news", "update", "example"],
            source_api="TestAPI",
            category=None,
            authors=["Alice Johnson", "Bob Lee"],
            related_countries=[],
            image_url="https://example.com/image2.jpg",
            post_processed=False,
        ),
    ]

    inserted_ids, errors = mongo_handler.insert_bulk_articles(articles)

    assert len(inserted_ids) == 2
    assert len(errors) == 0
    assert mongo_handler._articles.insert_many.called


@pytest.mark.unit
def test_insert_bulk_articles_failure(mongo_handler, mocker):
    mocker.patch.object(mongo_handler._articles, 'insert_many', side_effect=PyMongoError("Insert failed"))
    articles = [GlobeArticle(title="Test", url="https://example.com", description="Test",
                             date_published=datetime.now(timezone.utc),
                             provider="Test", language="en", content="Test", origin_country="US", source_api="Test")]
    inserted_ids, errors = mongo_handler.insert_bulk_articles(articles)
    assert len(inserted_ids) == 0
    assert len(errors) == 1
    assert errors[0]['error'] == 'Insert failed'


@pytest.mark.unit
def test_check_permissions_failure(mongo_handler, mocker):
    mocker.patch.object(mongo_handler._articles, 'find_one', side_effect=OperationFailure("No read permission"))
    with pytest.raises(OperationFailure):
        mongo_handler._check_permissions()


@pytest.mark.unit
def test_insert_bulk_articles_empty(mongo_handler):
    inserted_ids, errors = mongo_handler.insert_bulk_articles([])
    assert len(inserted_ids) == 0
    assert len(errors) == 0


@pytest.mark.unit
def test_insert_bulk_articles_execution_timeout(mongo_handler, mocker):
    mocker.patch.object(mongo_handler._articles, 'insert_many', side_effect=ExecutionTimeout("Timeout"))
    articles = [GlobeArticle(title="Test", url="https://example.com", description="Test",
                             date_published=datetime.now(timezone.utc),
                             provider="Test", language="en", content="Test", origin_country="US", source_api="Test")]
    inserted_ids, errors = mongo_handler.insert_bulk_articles(articles)
    assert len(inserted_ids) == 0
    assert len(errors) == 1
    assert errors[0]['error'] == 'Operation timed out'


@pytest.mark.unit
def test_insert_bulk_write_error(mongo_handler, mocker):
    mocker.patch.object(mongo_handler._articles, 'insert_many', side_effect=BulkWriteError({
        'writeErrors': [{'index': 0, 'errmsg': 'Duplicate key'}]
    }))
    articles = [GlobeArticle(title="Test", url="https://example.com", description="Test",
                             date_published=datetime.now(timezone.utc), provider="Test", language="en", content="Test",
                             origin_country="US", source_api="Test")]

    # Execute the function under test
    inserted_ids, errors = mongo_handler.insert_bulk_articles(articles)

    # Assert no IDs were inserted
    assert len(inserted_ids) == 0
    # Check that the error is correctly recorded
    assert len(errors) == 1
    assert errors[0]['error'] == 'Duplicate key'
