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
    def __init__(self, config: Config) -> None:
        self._logger = structlog.get_logger()
        self._subscription_key = config.BING_SEARCH_SUBSCRIPTION_KEY
        self._endpoint = config.BING_SEARCH_ENDPOINT
        self._countries = config.BING_SEARCH_COUNTRIES

    def _make_request(self, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
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
        Fetch trending news articles for a specific country, by providing no category in /news.
        This is what the Bing News API does by default when not providing information in /news.

        For more information refer to this query parameter documentation by Microsoft:
        https://learn.microsoft.com/en-us/bing/search-apis/bing-news-search/reference/query-parameters
        
        Args:
            **kwargs: Additional keyword arguments to pass to the Bing News API. (see API ref.)
            
        Returns:
            List[NewsSourceArticleData]: A list of NewsSourceArticle objects representing the trending news articles.
        """

        # ensure that if mkt is provided it contains a valid CountryAlpha2 code
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

    def _process_news_response(self, response: Dict[str, Any], cc: CountryAlpha2, lang: LanguageAlpha2) -> List[
        NewsSourceArticleData]:

        if 'value' in response:
            processed_response = [
                NewsSourceArticleData(
                    title=article.get('name', ''),
                    url=article.get('url', ''),
                    description=article.get('description'),
                    date_published=datetime.fromisoformat(article.get('datePublished')),
                    provider=article.get('provider', [{}])[0].get('name'),
                    image_url=article.get('image', {}).get('thumbnail', {}).get('contentUrl', '').split('&')[0] or None,
                    origin_country=cc,
                    language=lang,
                    source_api=self.__class__.__name__
                )
                for article in response.get('value', [])
            ]
            self._logger.debug(f'Processed {len(processed_response)} news articles from Bing News API')
            return processed_response
        else:
            raise BingNewsError('Failed to process news response from Bing News API')

    @property
    def available_countries(self) -> List[str]:
        return cast(List[str], self._countries)
