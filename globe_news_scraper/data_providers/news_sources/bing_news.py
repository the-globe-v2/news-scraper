# globe_news_scraper/data_providers/news_sources/bing_news.py
import requests
from typing import List, Dict, Any

import structlog

from globe_news_scraper.data_providers.news_sources.base import NewsSource, NewsSourceError


class BingNewsError(NewsSourceError):
    """Specific exception for Bing News errors"""


class BingNewsSource(NewsSource):
    def __init__(self, config):
        self.logger = structlog.get_logger()
        self.subscription_key = config.BING_SEARCH_SUBSCRIPTION_KEY
        self.endpoint = config.BING_SEARCH_ENDPOINT

    def _make_request(self, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        headers = {"Ocp-Apim-Subscription-Key": self.subscription_key}
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise BingNewsError(f"Bing News API request failed: {str(e)}")

    def get_trending_topics(self, **kwargs) -> List[Dict[str, Any]]:
        url = f"{self.endpoint}/v7.0/news/trendingtopics"
        params = {"mkt": kwargs.get("mkt", "en-US"), "count": kwargs.get("count", 100)}
        trending_topic_response = self._make_request(url, params)
        return self._process_trending_topics_response(trending_topic_response)

    def get_news_by_category(self, category: str, **kwargs) -> List[Dict[str, Any]]:
        url = f"{self.endpoint}/v7.0/news"
        params = {
            "category": category,
            "mkt": kwargs.get("mkt", "en-US"),
            "count": kwargs.get("count", 100),
            "freshness": kwargs.get("freshness", "Week"),
        }
        response = self._make_request(url, params)
        return self._process_news_response(response)

    def search_news(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        url = f"{self.endpoint}/v7.0/news/search"
        params = {
            "q": query,
            "mkt": kwargs.get("mkt", "en-US"),
            "count": kwargs.get("count", 100),
            "freshness": kwargs.get("freshness", "Month"),
        }
        response = self._make_request(url, params)
        return self._process_news_response(response)

    @staticmethod
    def _process_news_response(response: Dict[str, Any]) -> List[Dict[str, Any]]:
        if 'value' in response:
            processed_response = [
                {
                    'title': article.get('name'),
                    'url': article.get('url'),
                    'description': article.get('description'),
                    'date_published': article.get('datePublished'),
                    'provider': article.get('provider', [{}])[0].get('name'),
                    'image_url': (article.get('image', {})
                                  .get('thumbnail', {})
                                  .get('contentUrl', '').split('&')[0] or None),
                    'category': article.get('category'),
                }
                for article in response['value']
            ]
            return processed_response
        else:
            raise BingNewsError("Failed to process news response from Bing News API")

    @staticmethod
    def _process_trending_topics_response(trending_topics: Dict[str, Any]) -> List[Dict[str, Any]]:
        if 'value' in trending_topics:
            return [
                {
                    'name': topic.get('name'),
                    'query': topic.get('query', {}).get('text'),
                    'is_breaking_news': topic.get('isBreakingNews')
                }
                for topic in trending_topics['value']
            ]
        else:
            raise BingNewsError("Failed to process trending topics response from Bing News API")
