from pymongo import MongoClient, ASCENDING, DESCENDING
from globe_news_scraper.config import get_config


def setup_database():
    config = get_config()
    db_name = config.MONGO_DB
    client = MongoClient(config.MONGO_URI)

    try:
        db = client[db_name]
        articles = db.articles
        failed_articles = db.failed_articles

        articles.create_index("url", unique=True)
        articles.create_index("title")
        articles.create_index("date_published")
        articles.create_index("provider")
        articles.create_index("category")
        articles.create_index("language")
        articles.create_index("origin_country")
        articles.create_index([("post_processed", ASCENDING), ("date_scraped", DESCENDING)],
                              name="post_processed_date_scraped_idx")
        failed_articles.create_index("url", unique=True)
        failed_articles.create_index("date_published")
        failed_articles.create_index("failure_reason")

        # Check and drop the view if it exists before creating a new one
        if 'daily_article_summary_by_country' in db.list_collection_names():
            db.command("drop", "daily_article_summary_by_country")

        # Creating the view daily_article_summary_by_country
        db.command({
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

        # Check and drop the view if it exists before creating a new one
        if 'filtered_articles' in db.list_collection_names():
            db.command("drop", "filtered_articles")

        # Creating the view filtered_articles
        db.command({
            "create": "filtered_articles",
            "viewOn": "articles",
            "pipeline": [
                {"$match": {"post_processed": True}},
                {"$project": {
                    "title": "$title_translated",
                    "url": 1,
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

        # Confirmation of successful database setup
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
        print("Created views:")
        print("- articles_by_date_by_country (grouped by publication date)")
        print("- filtered_articles")

    except Exception as e:
        print("An error occurred while setting up the database:", e)
        client.close()
        raise
    finally:
        client.close()


if __name__ == "__main__":
    setup_database()
