# path: globe_news_scraper/database/mongo_handler.py
from datetime import datetime, timezone
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

    def __init__(self, config: Config, client: Optional[MongoClient] = None):
        """
        Initialize the MongoHandler with the provided configuration.

        :param config: Configuration object containing MongoDB settings.
        :param client: Optional MongoClient instance to use for the connection.
        :raises MongoHandlerError: If the MongoDB connection or any checks fail.
        """
        self._logger = structlog.get_logger()
        self._config = config
        try:
            self._client = client or MongoClient(self._config.MONGO_URI)
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
                IndexModel([("post_processed", ASCENDING), ("date_scraped", DESCENDING)],
                           name="post_processed_1_date_scraped_-1")
            ]

            # Create or update indexes
            for index in indexes:
                try:
                    self._articles.create_index(index.document["key"], unique=index.document.get("unique", False),
                                                name=index.document["name"])
                except OperationFailure as e:
                    if "already exists with different options" in str(e):
                        self._logger.warning(f"Updating existing index: {index.document['name']}")
                        self._articles.drop_index(index.document["name"])
                        self._articles.create_index(index.document["key"], unique=index.document.get("unique", False),
                                                    name=index.document["name"])
                    else:
                        raise

            # Create the views
            self._create_daily_summary_view()
            self._create_filtered_articles_view()

            # Create validation schema for the articles collection
            self._configure_schema_validation()

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

    def _configure_schema_validation(self) -> None:
        """
        Configure schema validation for the 'articles' and 'failed_articles' collections.

        This method sets up schema validation rules for both collections to ensure
        that documents adhere to a specific structure and data types. It defines a
        common base schema and applies additional fields for the 'failed_articles'
        collection.

        The method uses strict validation and will raise an error for any document
        that doesn't conform to the schema during insert or update operations.
        """
        base_required = ["title", "url", "description", "date_published", "provider", "content",
                         "origin_country", "source_api", "schema_version", "date_scraped", "post_processed"]

        base_properties = {
            "title": {"bsonType": "string", "description": "The headline or title of the article"},
            "title_translated": {"bsonType": ["string", "null"], "description": "The translated title of the article"},
            "url": {"bsonType": "string", "pattern": "^https?://\\S+$",
                    "description": "The web address where the article can be found"},
            "description": {"bsonType": "string",
                            "description": "A brief summary or description of the article's content"},
            "description_translated": {"bsonType": ["string", "null"],
                                       "description": "The translated description of the article"},
            "date_published": {"bsonType": "date",
                               "description": "The date and time when the article was originally published"},
            "provider": {"bsonType": "string",
                         "description": "The name of the news outlet or platform that published the article"},
            "language": {"bsonType": ["string", "null"], "pattern": "^[a-z]{2}$",
                         "description": "The primary language of the article's content, in ISO 639-1 format"},
            "content": {"bsonType": "string", "description": "The main body text of the article"},
            "origin_country": {"bsonType": "string", "pattern": "^[A-Z]{2}$",
                               "description": "The country where the article was published, in ISO 3166-1 alpha-2 format"},
            "keywords": {"bsonType": "array", "items": {"bsonType": "string"},
                         "description": "A list of relevant keywords or tags associated with the article"},
            "source_api": {"bsonType": "string",
                           "description": "The name or identifier of the API from which the article data was retrieved"},
            "schema_version": {"bsonType": "string",
                               "description": "The version of the data schema used to structure this article's information"},
            "date_scraped": {"bsonType": "date",
                             "description": "The date and time when the article was collected by the scraper"},
            "category": {"bsonType": ["string", "null"],
                         "description": "The topical category or section under which the article is classified"},
            "authors": {"bsonType": ["array", "null"], "items": {"bsonType": "string"},
                        "description": "A list of the article's authors or contributors"},
            "related_countries": {"bsonType": ["array", "null"],
                                  "items": {"bsonType": "string", "pattern": "^[A-Z]{2}$"},
                                  "description": "Countries mentioned or relevant to the article's content"},
            "image_url": {"bsonType": ["string", "null"], "pattern": "^https?://\\S+$",
                          "description": "The URL of the main image associated with the article"},
            "post_processed": {"bsonType": "bool",
                               "description": "Will be true once the article is curated by globe_news_locator"}
        }

        articles_schema = {
            "bsonType": "object",
            "required": base_required,
            "properties": base_properties
        }

        failed_articles_schema = {
            "bsonType": "object",
            "required": base_required + ["failure_reason"],
            "properties": {
                **base_properties,
                "_id": {"bsonType": "objectId", "description": "The unique identifier for the failed article"},
                "failure_reason": {"bsonType": "string", "description": "The reason why the article failed to process"}
            }
        }

        for collection, schema in [("articles", articles_schema),
                                   ("failed_articles", failed_articles_schema)]:
            self._db.command({
                "collMod": collection,
                "validator": {"$jsonSchema": schema},
                "validationLevel": "strict",
                "validationAction": "error"
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
        test_doc = {
            "_id": "test",
            "title": "Test Article Title",
            "url": "https://example.com/test-article",
            "description": "This is a test article description.",
            "date_published": datetime.now(timezone.utc),
            "provider": "Test News Provider",
            "content": "This is the main content of the test article.",
            "origin_country": "FR",
            "source_api": "test_api",
            "schema_version": "1.1",
            "date_scraped": datetime.now(timezone.utc),
            "post_processed": False,
            "language": "fr",
            "keywords": ["test", "article"],
            "category": "SOCIETY",
            "authors": ["Test Author"],
            "related_countries": ["DE", "ES"],
            "image_url": "https://example.com/test-image.jpg"
        }
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
                for error in bwe.details.get('writeErrors', []):
                    self._logger.error("MongoDB Bulk write error occurred",
                                       article_url=serialized_articles[error['index']]['url'])
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
