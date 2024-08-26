from pymongo import MongoClient, ASCENDING, DESCENDING
from globe_news_scraper.config import get_config

def setup_database():
    # Get the configuration from the config module (e.g., database name, URI, etc.)
    config = get_config()

    # Retrieve the database name from the configuration
    db_name = config.MONGO_DB

    # Establish a connection to the MongoDB server using the provided URI
    client = MongoClient(config.MONGO_URI)

    try:
        # Access the database with the specified name (it will be created if it doesn't exist)
        db = client[db_name]

        # Create or access the 'articles' collection where news articles will be stored
        articles = db.articles

        # Create or access the 'failed_articles' collection to log articles that failed to process
        failed_articles = db.failed_articles

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

        # Create indexes for the 'failed_articles' collection
        failed_articles.create_index("url", unique=True)
        failed_articles.create_index("date_published")
        failed_articles.create_index("failure_reason")

        try:
            # Create a MongoDB view for summarizing articles
            # This view groups articles by their publication date and country of origin
            db.command({
                'create': 'daily_article_summary_by_country',
                'viewOn': 'articles',  # Base collection for the view
                'pipeline': [  # Aggregation pipeline to generate the view
                    # Step 1: Project relevant fields for further processing
                    {
                        '$project': {
                            'date': {'$dateToString': {'format': "%Y-%m-%d", 'date': "$date_published"}},  # Format date as YYYY-MM-DD
                            'origin_country': 1,  # Include the country of origin
                            '_id': 1  # Include the article ID
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
                            'article_ids': {'$addToSet': '$_id'}  # Collect the article IDs in each group
                        }
                    },
                    # Step 3: Group results by date, creating an array of countries with their article counts and IDs
                    {
                        '$group': {
                            '_id': '$_id.date',  # Group by date
                            'countries': {
                                '$push': {  # Create an array of countries with their counts and article IDs
                                    'country': '$_id.origin_country',
                                    'count': '$count',
                                    'article_ids': '$article_ids'
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
            view_created = True
        except Exception as e:
            print(f"An error occurred while creating the view. The view may already exist: {e}")
            view_created = False

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
        if view_created:
            print("Created view:")
            print("- articles_by_date_by_country (grouped by publication date)")

    except Exception as e:
        # Exit disgracefully if problems arise.
        print(f"An error occurred while setting up the database: {e}")
        client.close()
        raise
    finally:
        client.close()

if __name__ == "__main__":
    setup_database()