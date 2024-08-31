# path: globe_news_scraper/data_providers/news_pipeline/__init__.py

from typing import List, Dict, Optional, cast
from concurrent.futures import ThreadPoolExecutor, as_completed

import structlog
from pymongo.errors import BulkWriteError

from globe_news_scraper.config import Config
from globe_news_scraper.models import GlobeArticle
from globe_news_scraper.monitoring import GlobeScraperTelemetry
from globe_news_scraper.database import MongoHandler
from globe_news_scraper.data_providers.news_pipeline.article_builder import ArticleBuilder
from globe_news_scraper.data_providers.news_sources.models import NewsSourceArticleData
from globe_news_scraper.data_providers.news_sources.base import NewsSource
from globe_news_scraper.data_providers.news_sources import NewsSourceFactory


class NewsPipeline:
    def __init__(self, config: Config, db_handler: MongoHandler, telemetry: GlobeScraperTelemetry) -> None:
        self._config = config
        self._logger = structlog.get_logger()
        self._news_sources = NewsSourceFactory.get_all_sources(self._config)
        self._article_builder = ArticleBuilder(self._config, telemetry)
        self._db_handler = db_handler

    def run_pipeline(self) -> List[str]:
        """
        Run the entire article pipeline for every available news source and country.

        Returns:
            List[str]: A list of Mongo ObjectIds for the inserted articles.
        """
        all_articles = []
        # Iterate through all news sources and all countries supported by each source
        for news_source in self._news_sources:
            for country_code in news_source.available_countries:
                try:
                    articles = self._process_country(news_source, country_code)
                    all_articles.extend(articles)
                    self._logger.info(
                        "Country processing complete",
                        news_source=news_source.__class__.__name__,
                        country_code=country_code,
                        articles_count=len(articles)
                    )
                except Exception as e:
                    self._logger.error(
                        "Failed to process country",
                        news_source=news_source.__class__.__name__,
                        country_code=country_code,
                        error=str(e)
                    )
        return all_articles

    def _process_country(self, news_source: NewsSource, target_country: str) -> List[str]:
        """
        Process a single country's trending news from a news source.

        Returns:
            List[str]: A list of Mongo ObjectIds for the inserted articles.
        """
        trending_news = news_source.get_country_trending_news(mkt=target_country)

        with ThreadPoolExecutor(max_workers=self._config.MAX_SCRAPING_WORKERS) as executor:
            future_to_item = {executor.submit(self._build_article, item): item for item in trending_news}
            built_articles = cast(List[GlobeArticle], [
                future.result() for future in as_completed(future_to_item)
                if future.result() is not None
            ])

        inserted_articles = self._bulk_insert_articles(built_articles)

        self._log_country_processing_stats(target_country, trending_news, built_articles, inserted_articles)

        return inserted_articles

    def _build_article(self, news_item: NewsSourceArticleData) -> Optional[GlobeArticle]:
        """
        Build a GlobeArticle object from news item data if it doesn't already exist in the database.

        Args:
            news_item (NewsSourceArticleData): A news item data object from a news source.

        Returns:
            Optional[GlobeArticle]: A GlobeArticle object if successfully built, None if already in DB or otherwise.
        """
        if self._db_handler.does_article_exist(news_item.url):
            self._logger.debug(f"Article already exists in the database, skipping: {news_item.url}")
            return None

        try:
            return self._article_builder.build(news_item)
        except Exception as e:
            self._logger.error(
                "Failed to build article",
                url=news_item.url,
                error=str(e)
            )
            return None

    def _bulk_insert_articles(self, articles: List[GlobeArticle]) -> List[str]:
        """
        Insert multiple articles into the database using a bulk operation.
        """
        try:
            return self._db_handler.insert_bulk_articles(articles)[0]
        except BulkWriteError as bwe:
            self._logger.error(
                "Bulk insert partially failed",
                error=str(bwe),
                failed_inserts=len(bwe.details['writeErrors'])
            )
            # Extract successfully inserted ObjectIds from BulkWriteError details
            successful_inserts = bwe.details.get('insertedIds', {})
            return [str(obj_id) for obj_id in successful_inserts.values()]
        except Exception as e:
            self._logger.error(
                "Bulk insert failed",
                error=str(e)
            )
            return []

    def _log_country_processing_stats(self, country: str, trending_news: List[NewsSourceArticleData],
                                      built_articles: List[GlobeArticle],
                                      inserted_articles: List[str]) -> None:
        """
        Log statistics for country processing.
        """
        self._logger.info(
            "Country processing statistics",
            country=country,
            total_trending_news=len(trending_news),
            articles_built=len(built_articles),
            articles_inserted=len(inserted_articles),
            build_success_rate=f"{len(built_articles) / len(trending_news):.2%}",
            insert_success_rate=f"{len(inserted_articles) / len(built_articles):.2%}" if built_articles else "N/A"
        )
