## README.md

# Globe News Scraper

Welcome to the Globe News Scraper, a Python-based tool designed to efficiently scrape, process, and store news articles from various sources. This project is designed to run in a containerized environment and is capable of handling large volumes of data while ensuring robustness and resilience.

## Overview

The Globe News Scraper is a comprehensive news scraping tool that integrates multiple components for fetching, processing, and storing news articles from various sources. It uses a pipeline architecture that handles everything from data acquisition to database storage, ensuring that articles are scraped and processed efficiently.

- **Key Features**:
  - Scalable architecture designed for containerized environments.
  - Parallel processing of articles using thread pools.
  - Robust error handling and logging mechanisms.
  - Support for multiple news sources, with easy extensibility for future sources.

For more details on the codebase, refer to the following sections of the documentation:

- [System Architecture](https://mavial.notion.site/Globe-News-Scraper-95c5f9dfe79944599b63d719024a35df)
- [Configuration](https://mavial.notion.site/Globe-News-Scraper-95c5f9dfe79944599b63d719024a35df)
- [Setup and Deployment](https://mavial.notion.site/Globe-News-Scraper-95c5f9dfe79944599b63d719024a35df)
- [Logging](https://mavial.notion.site/Globe-News-Scraper-95c5f9dfe79944599b63d719024a35df)

## System Architecture

### Deployment Architecture

The Globe News Scraper is designed for deployment in a containerized environment using Docker. It can be scheduled to run periodically using cron jobs or similar scheduling tools.

### Data Flow

The data flow within the Globe News Scraper is managed by the `NewsPipeline` class, which orchestrates the fetching, processing, and storing of news articles.

- **Data Acquisition**: Handled by the `NewsPipeline` class, which coordinates with news sources to fetch articles.
- **Data Processing**: Articles are processed by the `ArticleBuilder` component, which validates and structures the data.
- **Data Storage**: Processed articles are stored in a MongoDB database using the `MongoHandler`.

For a detailed view of the components and their interactions, refer to the [System Architecture section](#system-architecture) in the documentation.

### Core Components

- **`NewsPipeline`**: Orchestrates the entire scraping process.
- **`ArticleBuilder`**: Handles the processing and validation of articles.
- **`MongoHandler`**: Manages the storage of articles in MongoDB.
- **`NewsSourceFactory`**: Manages the creation of news source objects.

Refer to the [Core Components section](https://mavial.notion.site/Globe-News-Scraper-95c5f9dfe79944599b63d719024a35df) for more details on each component, including key methods and performance considerations.

## Configuration

The Globe News Scraper uses a centralized `Config` class, built with Pydantic, to manage all configurations. The configuration settings cover various aspects of the application, such as logging, database connections, and scraping parameters.

- **Environment Variable Management**: Configuration values are automatically loaded from environment variables, with defaults set in a `.env` file.
- **Type Validation**: Ensures that all configurations are correctly typed and validated at startup.

For detailed information on configuration options and their usage, visit the [Configuration section](https://mavial.notion.site/Globe-News-Scraper-95c5f9dfe79944599b63d719024a35df).

## Setup and Deployment

### Prerequisites

- Python 3.12+
- Docker (for containerized deployment)
- MongoDB

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/globe-news-scraper.git
   cd globe-news-scraper
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Database Initialization

Before running the scraper for the first time, initialize the database:

```bash
python -m globe_news_scraper.database.db_init --env prod
```

### Running the Scraper

To run the scraper locally:

```bash
python main.py --env prod --cron-schedule "0 2 * * *" --run-now
```

Command-line arguments:
- `--env`: Specify the environment (dev/prod/test)
- `--log-level`: Set the logging level
- `--cron-schedule`: Set the cron schedule
- `--run-now`: Run the scraper immediately on startup

### Docker Deployment

1. Build the Docker image:
   ```bash
   docker build -t globe-news-scraper .
   ```

2. Run the container:
   ```bash
   docker run -e SCRAPER_ENV=prod -e SCRAPER_CRON_SCHEDULE="0 2 * * *" globe-news-scraper
   ```

## Logging

Logging in the Globe News Scraper is managed through a combination of Python’s standard `logging` module and `structlog`. The logging configuration is flexible, allowing different formats for development and production environments.

## Database Structure

The MongoDB database includes the following key components:
- `articles` collection: Stores the scraped articles.
- `failed_articles` collection: Stores articles that failed to post process.
- `daily_article_summary_by_country` view: Provides a summary of articles by date and country.
- `filtered_articles` view: Displays only post-processed articles with translated fields.


For more details on configuring and using logging, visit the [Logging section](https://mavial.notion.site/Globe-News-Scraper-95c5f9dfe79944599b63d719024a35df).