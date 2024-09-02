# path: globe_news_scraper/database/mongo_handler.py
from enum import unique
from typing import List, Dict, Any, Tuple, Optional

import structlog
from pymongo import MongoClient, IndexModel, ASCENDING, DESCENDING
from pymongo.errors import BulkWriteError, PyMongoError, ExecutionTimeout, OperationFailure

from globe_news_scraper.config import Config
from globe_news_scraper.models import GlobeArticle


class MongoHandlerError(Exception):
    """Custom exception for MongoHandler errors."""


class MongoHandler:
    """
    A handler class for managing MongoDB operations related to GlobeArticle objects.

    This class is responsible for establishing a connection to a MongoDB database,
    checking necessary permissions, and providing methods for inserting and querying articles.
    """

    def __init__(self, config: Config) -> None:
        """
        Initialize the MongoHandler with the provided configuration.

        :param config: Configuration object containing MongoDB settings.
        :raises MongoHandlerError: If the MongoDB connection or any checks fail.
        """
        self._logger = structlog.get_logger()
        self._config = config
        try:
            # Establish connection
            self._client: MongoClient = MongoClient(self._config.MONGO_URI)
            self._db = self._client[self._config.MONGO_DB]
            self._articles = self._db.articles

            # Check connection
            self._client.admin.command('ping')

            # Check database existence
            if self._config.MONGO_DB not in self._client.list_database_names():
                raise MongoHandlerError(f"Database '{self._config.MONGO_DB}' does not exist")

            # Check collection existence
            if 'articles' not in self._db.list_collection_names():
                raise MongoHandlerError("Collection 'articles' does not exist")

            # Check permissions
            self._check_permissions()

            self._logger.info("MongoDB connection and permissions verified successfully")
        except PyMongoError as e:
            raise MongoHandlerError(f"Failed to initialize MongoDB connection: {str(e)}")
        except Exception as e:
            raise MongoHandlerError(f"Unexpected error occurred: {str(e)}")

    def initialize_database(self) -> None:
        """Initialize the database with necessary collections and indexes."""
        try:
            # Define the indexes we want to create
            indexes = [
                IndexModel([("url", ASCENDING)], unique=True, name="url_1"),
                IndexModel([("title", ASCENDING)], unique=True, name="title_1"),
                IndexModel([("date_published", DESCENDING)], name="date_published_-1"),
                IndexModel([("category", ASCENDING)], name="category_1"),
                IndexModel([("origin_country", ASCENDING)], name="origin_country_1"),
                IndexModel([("post_processed", ASCENDING), ("date_scraped", DESCENDING)], name="post_processed_1_date_scraped_-1")
            ]

            # Create or update indexes
            for index in indexes:
                try:
                    self._articles.create_index(index.document["key"], unique=index.document.get("unique", False), name=index.document["name"])
                except OperationFailure as e:
                    if "already exists with different options" in str(e):
                        self._logger.warning(f"Updating existing index: {index.document['name']}")
                        self._articles.drop_index(index.document["name"])
                        self._articles.create_index(index.document["key"], unique=index.document.get("unique", False), name=index.document["name"])
                    else:
                        raise

            # Create the views
            self._create_daily_summary_view()
            self._create_filtered_articles_view()

            self._logger.info("Database initialized successfully")
        except PyMongoError as e:
            raise MongoHandlerError(f"Failed to initialize database: {str(e)}")

    def _create_daily_summary_view(self) -> None:
        """
        Create the daily_article_summary_by_country view, used by The Globe app to preload artice urls.
        """
        self._db.command({
            'create': 'daily_article_summary_by_country',
            'viewOn': 'articles',
            'pipeline': [
                # Step 1: Project relevant fields for further processing
                {
                    '$project': {
                        'date': {'$dateToString': {'format': "%Y-%m-%d", 'date': "$date_published"}},
                        'origin_country': 1,  # Include the country of origin
                        'url': 1  # Include the URL field
                    }
                },
                # Step 2: Group articles by date and country of origin, and count the number of articles per group
                {
                    '$group': {
                        '_id': {
                            'date': '$date',  # Group by formatted date
                            'origin_country': '$origin_country'  # Group by country of origin
                        },
                        'count': {'$sum': 1},  # Count the number of articles in each group
                        'article_urls': {'$addToSet': '$url'}  # Collect the article urls in each group
                    }
                },
                # Step 3: Group results by date, creating an array of countries with their article counts and URLs
                {
                    '$group': {
                        '_id': '$_id.date',  # Group by date
                        'countries': {
                            '$push': {  # Create an array of countries with their counts and article urls
                                'country': '$_id.origin_country',
                                'count': '$count',
                                'article_urls': '$article_urls'
                            }
                        },
                        'total_count': {'$sum': '$count'}  # Calculate the total number of articles for the date
                    }
                },
                # Step 4: Project the final structure of the view
                {
                    '$project': {
                        '_id': 0,  # Exclude the MongoDB auto-generated ID
                        'date': '$_id',  # Include the date
                        'countries': 1,  # Include the array of countries with their article data
                        'total_count': 1  # Include the total count of articles for the date
                    }
                },
                # Step 5: Sort the results by date in descending order
                {
                    '$sort': {'date': -1}  # Sort by date (newest first)
                }
            ]
        })

    def _create_filtered_articles_view(self) -> None:
        """
        Create the filtered_articles view to display only post-processed articles with translated fields.
        """
        self._db.command({
            "create": "filtered_articles",
            "viewOn": "articles",
            "pipeline": [
                {"$match": {"post_processed": True}},
                {"$project": {
                    "url": 1,
                    "title": "$title_translated",
                    "description": "$description_translated",
                    "date_published": 1,
                    "provider": 1,
                    "language": 1,
                    "origin_country": 1,
                    "keywords": 1,
                    "category": 1,
                    "authors": 1,
                    "related_countries": 1,
                    "image_url": 1,
                    "_id": 0
                }}
            ]
        })

    def _check_permissions(self) -> None:
        """
        Check the necessary permissions for the MongoDB operations.

        This method checks if the MongoDB user has the required permissions to perform
        read, write, and index creation operations on the 'articles' collection.

        :raises OperationFailure: If any of the permissions checks fail.
        """
        # Check read permission
        self._articles.find_one()

        # Check write permission
        test_doc = {"_id": "test", "test": True}
        self._articles.insert_one(test_doc)
        self._articles.delete_one({"_id": "test"})

        # Check index creation permission
        self._articles.create_index("url", unique=True)
        self._articles.drop_index("url_1")

    def insert_bulk_articles(self, articles: List[GlobeArticle]) -> Tuple[List[Any], List[Dict[str, Any]]]:
        """
        Insert multiple GlobeArticle objects into the MongoDB collection, returning the inserted IDs and any errors.

        Before inserting, the GlobeArticle objects are serialized to a dictionary for compatibility with MongoDB.

        :param articles: A list of GlobeArticle objects to insert.
        :return: A tuple containing the inserted IDs and any errors that occurred.
        """
        serialized_articles = [self._serialize_article(article) for article in articles]
        errors: List[Dict[str, Any]] = []
        inserted_ids: List[Any] = []

        if serialized_articles:
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
        else:
            self._logger.debug("No articles to insert.")

        return inserted_ids, errors

    def does_article_exist(self, url: str) -> bool:
        """
        Check if an article with the given URL already exists in the MongoDB collection.

        :param url: The URL of the article to check.
        :return: True if the article exists, False otherwise.
        """
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
        """
        Serialize a GlobeArticle object to a dictionary for MongoDB insertion.

        This method converts a GlobeArticle object to a dictionary and ensures that
        certain fields are properly formatted for storage in MongoDB.

        :param article: The GlobeArticle object to serialize.
        :return: A dictionary representing the serialized article.
        """
        serialized_article = article.model_dump()
        serialized_article.update({
            'url': str(article.url),
            'image_url': str(article.image_url) if article.image_url else None,
        })
        return serialized_article
