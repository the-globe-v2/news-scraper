# globe_news_scraper/data_providers/news_sources/bing_news.py

import time
import requests
from datetime import datetime
from typing import List, Dict, Any, cast
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

import structlog
from pycountry import countries, languages
from pydantic_extra_types.country import CountryAlpha2
from pydantic_extra_types.language_code import LanguageAlpha2

from globe_news_scraper.config import Config
from globe_news_scraper.data_providers.news_sources.models import NewsSourceArticleData
from globe_news_scraper.data_providers.news_sources.base import NewsSource, NewsSourceError


class BingNewsError(NewsSourceError):
    """Specific exception for Bing News errors"""


class BingNewsRateLimitError(BingNewsError):
    """Specific exception for Bing News rate limit errors"""


class BingNewsSource(NewsSource):
    """
    A data provider class for fetching news articles from the Bing News API.

    This class handles making requests to the Bing News API, processing the responses,
    and managing rate limits using retries. It supports fetching trending news articles
    for specific countries.
    """

    def __init__(self, config: Config) -> None:
        """
        Initialize the BingNewsSource with the provided configuration.

        :param config: Configuration object containing Bing News API settings.
        """
        self._logger = structlog.get_logger()
        self._subscription_key = config.BING_SEARCH_SUBSCRIPTION_KEY
        self._endpoint = config.BING_SEARCH_ENDPOINT
        self._countries = config.BING_SEARCH_COUNTRIES

    def _make_request(self, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make a GET request to the Bing News API with the specified URL and parameters.

        :param url: The URL endpoint for the Bing News API request.
        :param params: A dictionary of query parameters to include in the request.
        :return: The JSON response from the API as a dictionary.
        :raises BingNewsRateLimitError: If the API rate limit is exceeded (HTTP 429).
        :raises BingNewsError: If any other request exception occurs.
        """
        headers = {'Ocp-Apim-Subscription-Key': self._subscription_key}
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()  # Raise an exception for 4xx and 5xx status codes
            return cast(Dict[str, Any], response.json())
        except requests.RequestException as e:
            if e.response and e.response.status_code == 429:
                raise BingNewsRateLimitError("Rate limit exceeded.") from e
            raise BingNewsError(f"Bing News API request failed: {str(e)}") from e

    @retry(
        wait=wait_exponential(multiplier=1, min=4, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(BingNewsRateLimitError)
    )
    def get_country_trending_news(self, **kwargs: Any) -> List[NewsSourceArticleData]:
        """
        Fetch trending news articles for a specific country by making a request to the Bing News API.

        The method retries on rate limit errors, using exponential backoff. If no 'mkt' parameter is provided,
        the default 'en-US' market is used.

        :param kwargs: Additional keyword arguments to pass to the Bing News API.
        :return: A list of NewsSourceArticleData objects representing the trending news articles.
        :raises BingNewsError: If the market ('mkt') parameter is invalid or any other error occurs.
        """

        # Ensure that if 'mkt' is provided, it contains a valid CountryAlpha2 code
        mkt = kwargs.get('mkt', 'en-US')
        lang_code, country_code = mkt.split('-')
        cc = countries.get(alpha_2=country_code).alpha_2
        lang = languages.get(alpha_2=lang_code).alpha_2

        if not cc and not lang:
            raise BingNewsError(f'Invalid "mkt" param provided for BingNewsSource: {mkt}')

        url = f'{self._endpoint}/v7.0/news'
        params = {
            'mkt': mkt,
            'sortBy': kwargs.get('sortBy', 'Relevance'),
            'safeSearch': kwargs.get('safeSearch', 'Off'),
        }
        trending_topic_response = self._make_request(url, params)

        # Wait for 1 second to avoid rate limiting (HTTP 429)
        time.sleep(1)
        return self._process_news_response(trending_topic_response, cc, lang)

    def _process_news_response(self, response: Dict[str, Any], cc: CountryAlpha2, lang: LanguageAlpha2) -> List[NewsSourceArticleData]:
        """
        Process the response from the Bing News API into a list of NewsSourceArticleData objects.

        :param response: The JSON response from the Bing News API.
        :param cc: The country code (alpha-2) for the articles.
        :param lang: The language code (alpha-2) for the articles.
        :return: A list of NewsSourceArticleData objects representing the articles.
        :raises BingNewsError: If an error occurs while processing the response.
        """
        try:
            processed_response = [
                NewsSourceArticleData(
                    title=article.get('name', ''),
                    url=article.get('url', ''),
                    description=article.get('description'),
                    date_published=datetime.fromisoformat(article.get('datePublished')),
                    provider=article.get('provider', [{}])[0].get('name', 'MSN'),
                    image_url=article.get('image', {}).get('thumbnail', {}).get('contentUrl', '').split('&')[0] or None,
                    origin_country=cc,
                    language=lang,
                    source_api=self.__class__.__name__
                )
                for article in response.get('value', [])
            ]
            self._logger.debug(f'Processed {len(processed_response)} news articles from Bing News API')
            return processed_response
        except Exception as e:
            raise BingNewsError(f'Failed to process news response from Bing News API: {e}')

    @property
    def available_countries(self) -> List[str]:
        """
        Get the list of available countries in the BingNews search api.

        :return: A list of country codes available in the BingNews search api.
        """
        return cast(List[str], self._countries)
