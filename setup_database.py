# path: globe_news_scraper/setup_database.py
import os

from pymongo import MongoClient, ASCENDING, DESCENDING
from typing import Literal, cast
from globe_news_scraper.config import get_config


def setup_database():
    # Get the environment, use 'development' as default
    environment = os.getenv('ENV', 'dev')
    if environment not in ['dev', 'prod', 'test']:
        raise ValueError("Invalid environment. Use 'dev', 'prod', or 'test'.")

    # Get the configuration
    config = get_config(cast(Literal['dev', 'prod', 'test'], environment))

    # Get the database name
    db_name = config.MONGO_DB

    # Connect to MongoDB
    client = MongoClient(config.MONGO_URI)

    try:
        # Create or get the database
        db = client[db_name]

        # Create collections
        articles = db.articles

        # Create indexes
        articles.create_index("url", unique=True)
        articles.create_index("title")
        articles.create_index("date_published")
        articles.create_index("provider")
        articles.create_index("category")

        # Create new compound index to later filter out curated articles
        articles.create_index([("llm_curated", ASCENDING), ("date_scraped", DESCENDING)],
                              name="llm_curated_date_scraped_idx")

        print(f"Database setup completed successfully for environment: {environment}")
        print(f"Database name: {db_name}")
        print("Created indexes:")
        print("- url (unique)")
        print("- date_published")
        print("- provider")
        print("- category")
        print("- llm_curated_date_scraped_idx (compound: llm_curated ASC, date_scraped DESC)")

    except Exception as e:
        print(f"An error occurred while setting up the database: {e}")
    finally:
        client.close()


if __name__ == "__main__":
    setup_database()