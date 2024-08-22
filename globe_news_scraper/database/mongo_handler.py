# path: globe_news_scraper/database/mongo_handler.py

from typing import List, Dict, Any, Tuple, Optional, cast

import structlog
from pymongo import MongoClient
from pymongo.errors import BulkWriteError, PyMongoError, ExecutionTimeout

from globe_news_scraper.config import Config
from globe_news_scraper.models import GlobeArticle


class MongoHandlerError(Exception):
    """Custom exception for MongoHandler errors."""


class MongoHandler:
    def __init__(self, config: Config) -> None:
        self._logger = structlog.get_logger()
        try:
            self._client: MongoClient = MongoClient(config.MONGO_URI)
            self._db = self._client[config.MONGO_DB]
            self._articles = self._db.articles
        except PyMongoError as e:
            self._logger.critical(f"MongoDB connection error: {str(e)}")
            raise MongoHandlerError(f"MongoDB connection error: {str(e)}")

    def initialize(self) -> None:
        try:
            # Check if the database exists
            db_names = self._client.list_database_names()
            if self._db.name not in db_names:
                raise MongoHandlerError(f"Database '{self._db.name}' does not exist")

            # Check if the collection exists
            collection_names = self._db.list_collection_names()
            if self._articles.name not in collection_names:
                raise MongoHandlerError(f"Collection '{self._articles.name}' does not exist")

            # Check if required indexes exist
            # TODO: Add check for compound index
            required_indexes = ["url", "title", "date_published", "provider", "category"]
            existing_indexes = self._articles.index_information()

            for index in required_indexes:
                if f"{index}_1" not in existing_indexes:
                    raise MongoHandlerError(f"Required index '{index}' does not exist")

            self._logger.info("Database initialization successful.")
        except Exception as e:
            self._logger.critical(f"Database initialization failed: {str(e)}")
            raise MongoHandlerError(f"Database initialization failed: {str(e)}")

    def insert_bulk_articles(self, articles: List[GlobeArticle]) -> Tuple[List[Any], List[Dict[str, Any]]]:
        """
        Insert multiple GlobeArticle objects into the MongoDB collection, returning the inserted IDs and any errors.
        Before inserting, the GlobeArticle objects are serialized to a dictionary for compatibility with MongoDB.

        Args:
            articles (List[GlobeArticle]): A list of GlobeArticle objects to insert.

        Returns:
            Tuple[List[Any], List[Dict[str, Any]]]: A tuple containing the inserted IDs and any errors that occurred.
        """
        serialized_articles = [self._serialize_article(article) for article in articles]
        errors: List[Dict[str, Any]] = []
        inserted_ids: List[Any] = []

        try:
            result = self._articles.insert_many(serialized_articles, ordered=False)
            inserted_ids = result.inserted_ids
        except BulkWriteError as bwe:
            self._logger.error("MongoDB Bulk write error occurred", exc_info=True)

            for error in bwe.details.get('writeErrors', []):
                errors.append({
                    'index': error['index'],
                    'url': serialized_articles[error['index']]['url'],
                    'error': error['errmsg']
                })
            # Use insertedIds from BulkWriteError details if available
            inserted_ids = bwe.details.get('insertedIds', [])
        except ExecutionTimeout:
            self._logger.error("Bulk write operation timed out", exc_info=True)
            errors.append({'error': 'Operation timed out'})
        except Exception as e:
            self._logger.error(f"Unexpected error occurred: {e}", exc_info=True)
            errors.append({'error': str(e)})

        if not inserted_ids:
            self._logger.error(f"Failed to insert any articles to {self._db}")
        elif errors:
            self._logger.warning(f"Inserted {len(inserted_ids)} articles, but {len(errors)} failed")
        else:
            self._logger.info(f"Successfully inserted all {len(inserted_ids)} articles")

        return inserted_ids, errors

    def does_article_exist(self, url: str) -> bool:
        try:
            return self._articles.count_documents({"url": url}, limit=1) > 0
        except PyMongoError as e:
            self._logger.error(f"MongoDB error while checking article existence: {url}. Error: {str(e)}")
            return False
        except Exception as e:
            self._logger.error(f"Unexpected error while checking article existence: {url}. Error: {str(e)}")
            return False

    @staticmethod
    def _serialize_article(article: GlobeArticle) -> Dict[str, Any]:
        serialized_article = article.model_dump()
        serialized_article.update({
            'url': str(article.url),
            'image_url': str(article.image_url) if article.image_url else None,
        })
        return serialized_article
