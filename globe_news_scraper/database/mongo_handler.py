# path: globe_news_scraper/database/mongo_handler.py

from typing import List, Dict, Any, cast

import structlog
from pymongo import MongoClient

from globe_news_scraper.config import Config
from globe_news_scraper.models import GlobeArticle


class MongoHandlerError(Exception):
    """Custom exception for MongoHandler errors."""


class MongoHandler:
    def __init__(self, config: Config) -> None:
        self.logger = structlog.get_logger()
        self.client: MongoClient = MongoClient(config.MONGO_URI)
        self.db = self.client[config.MONGO_DB]
        self.articles = self.db.articles

    def initialize(self) -> None:
        try:
            # Check if the database exists
            db_names = self.client.list_database_names()
            if self.db.name not in db_names:
                raise MongoHandlerError(f"Database '{self.db.name}' does not exist")

            # Check if the collection exists
            collection_names = self.db.list_collection_names()
            if self.articles.name not in collection_names:
                raise MongoHandlerError(f"Collection '{self.articles.name}' does not exist")

            # Check if required indexes exist
            required_indexes = ["url", "date_published", "provider", "keywords", "category"]
            existing_indexes = self.articles.index_information()

            for index in required_indexes:
                if f"{index}_1" not in existing_indexes:
                    raise MongoHandlerError(f"Required index '{index}' does not exist")

            self.logger.info("Database initialization successful.")
        except Exception as e:
            self.logger.critical(f"Database initialization failed: {str(e)}")
            raise MongoHandlerError(f"Database initialization failed: {str(e)}")

    def insert_article(self, article: GlobeArticle) -> str:
        article_dict = article.model_dump()
        result = self.articles.insert_one(article_dict)

        # TODO: Improve error handling.

        if result.inserted_id is None:
            raise MongoHandlerError(f"Failed to insert article to {self.db}.")
        else:
            return cast(str, result.inserted_id)

    def insert_bulk_articles(self, articles: list) -> List[str]:
        serialized_articles = [self._serialize_article(article) for article in articles]
        result = self.articles.insert_many(serialized_articles)

        if len(result.inserted_ids) == 0:
            raise MongoHandlerError(f"Failed to insert any articles to {self.db}.")
        elif len(serialized_articles) != len(result.inserted_ids):
            raise MongoHandlerError(f"Failed to insert all articles to {self.db}.")

        return result.inserted_ids

    def does_article_exist(self, url: str) -> bool:
        return self.articles.count_documents({"url": url}) > 0

    @staticmethod
    def _serialize_article(article: GlobeArticle) -> Dict[str, Any]:
        serialized_article = article.model_dump()
        serialized_article.update({
            'url': str(article.url),
            'image_url': str(article.image_url) if article.image_url else None,
        })
        return cast(Dict[str, Any], serialized_article)
