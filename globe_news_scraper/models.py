# path: globe_news_scraper/models.py

from pydantic import BaseModel, HttpUrl, Field
from pydantic_extra_types.country import CountryAlpha2
from pydantic_extra_types.language_code import LanguageAlpha2
from typing import Optional, List, Any, Annotated
from datetime import datetime

from goose3 import Article  # type: ignore[import-untyped]

from globe_news_scraper.version import CURRENT_SCHEMA_VERSION


class GlobeArticle(BaseModel):
    """
    Represents a news article with various attributes.

    This class encapsulates all relevant information about a news article,
    including its content, metadata, and source information.

    Attributes:
        title (str): The headline or title of the article.
        url (Annotated[str, HttpUrl]): The web address where the article can be found.
        description (str): A brief summary or description of the article's content.
        date_published (datetime): The date and time when the article was originally published.
        provider (str): The name of the news outlet or platform that published the article.
        language (Optional[LanguageAlpha2]): The primary language of the article's content, in ISO 639-1 format.
        content (str): The main body text of the article.
        origin_country (CountryAlpha2): The country where the article was published, in ISO 3166-1 alpha-2 format.
        keywords (List[str]): A list of relevant keywords or tags associated with the article.
        source_api (str): The name or identifier of the API from which the article data was retrieved.
        schema_version (str): The version of the data schema used to structure this article's information.
        date_scraped (datetime): The date and time when the article was collected by the scraper.
        category (Optional[str]): The topical category or section under which the article is classified.
        authors (Optional[List[str]]): A list of the article's authors or contributors.
        related_countries (Optional[List[CountryAlpha2]]): Countries mentioned or relevant to the article's content.
        image_url (Optional[Annotated[str, HttpUrl]): The URL of the main image associated with the article.
        post_processed (bool): (irrelevant to this module) Will be true once the article is curated by globe_news_locator.
    """

    title: str
    title_translated: Optional[str] = None
    url: Annotated[str, HttpUrl]
    description: str
    description_translated: Optional[str] = None
    date_published: datetime
    provider: str
    language: Optional[LanguageAlpha2]
    content: str
    origin_country: CountryAlpha2
    keywords: List[str] = Field(default_factory=list)
    source_api: str
    schema_version: str = Field(default=CURRENT_SCHEMA_VERSION)
    date_scraped: datetime = Field(default_factory=datetime.now)
    category: Optional[str] = None
    authors: Optional[List[str]] = None
    related_countries: Optional[List[CountryAlpha2]] = None
    image_url: Optional[Annotated[str, HttpUrl]] = None
    post_processed: bool = False


class ArticleData(BaseModel):
    """
    Holds all relevant data extracted from goose3.Article object for further processing.

    Attributes:
        cleaned_text (str): The cleaned and preprocessed text content of the article.
        meta_lang (Optional[LanguageAlpha2]): The language of the article's metadata, in ISO 639-1 format.
        meta_keywords (str): A string representation of the article's metadata keywords.
        authors (List[str]): A list of the article's authors or contributors.
        top_image (Optional[Annotated[str, HttpUrl]]): The URL of the main image associated with the article.
    """
    cleaned_text: str
    meta_lang: Optional[LanguageAlpha2]
    meta_keywords: str
    authors: List[str]
    top_image: Optional[Annotated[str, HttpUrl]]
