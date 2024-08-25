# path: globe_news_scraper/setup_database.py

from pymongo import MongoClient, ASCENDING, DESCENDING
from globe_news_scraper.config import get_config


def setup_database():
    # Get the configuration
    config = get_config()

    # Get the database name
    db_name = config.MONGO_DB

    # Connect to MongoDB
    client = MongoClient(config.MONGO_URI)

    try:
        # Create or get the database
        db = client[db_name]

        # Create collections
        articles = db.articles
        failed_articles = db.failed_articles  # New collection for failed articles

        # Create indexes for articles collection
        articles.create_index("url", unique=True)
        articles.create_index("title")
        articles.create_index("date_published")
        articles.create_index("provider")
        articles.create_index("category")
        articles.create_index("language")
        articles.create_index("origin_country")
        articles.create_index([("post_processed", ASCENDING), ("date_scraped", DESCENDING)],
                              name="post_processed_date_scraped_idx")

        # Create indexes for failed_articles collection
        failed_articles.create_index("url", unique=True)
        failed_articles.create_index("date_published")
        failed_articles.create_index("failure_reason")

        print(f"Database setup completed successfully for: {config.MONGO_DB}")
        print(f"Database name: {db_name}")
        print("Created collections:")
        print("- articles")
        print("- failed_articles")
        print("Created indexes for articles:")
        print("- url (unique)")
        print("- title")
        print("- date_published")
        print("- provider")
        print("- category")
        print("- language")
        print("- origin_country")
        print("- post_processed_date_scraped_idx (compound: post_processed ASC, date_scraped DESC)")
        print("Created indexes for failed_articles:")
        print("- url (unique)")
        print("- date_published")
        print("- failure_reason")

    except Exception as e:
        print(f"An error occurred while setting up the database: {e}")
    finally:
        client.close()


if __name__ == "__main__":
    setup_database()