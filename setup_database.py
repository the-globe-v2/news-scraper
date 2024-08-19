# path: globe_news_scraper/scripts/setup_database.py
import os
import sys
from pymongo import MongoClient
from typing import Literal, cast
from globe_news_scraper.config import get_config

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def setup_database():
    # Change the working directory to the globe_news_scraper package
    os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'globe_news_scraper'))

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
        articles.create_index("date_published")
        articles.create_index("provider")
        articles.create_index("keywords")
        articles.create_index("category")

        print(f"Database setup completed successfully for environment: {environment}")
        print(f"Database name: {db_name}")

    except Exception as e:
        print(f"An error occurred while setting up the database: {e}")
    finally:
        client.close()


if __name__ == "__main__":
    setup_database()
