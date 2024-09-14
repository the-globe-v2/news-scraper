# globe_news_scraper/data_providers/news_sources/models.py

from datetime import datetime
from typing import Optional, Annotated

from pydantic import BaseModel, HttpUrl, Field, ConfigDict
from pydantic_extra_types.country import CountryAlpha2
from pydantic_extra_types.language_code import LanguageAlpha2


class NewsSourceArticleData(BaseModel):
    """
    Model representing the data structure for news articles retrieved from the different news apis.

    This model includes fields for the title, URL, description, publication date, provider,
    origin country, image URL, language, and the source API that fetched the article.
    """
    model_config = ConfigDict(frozen=True)

    title: str = Field(..., description="Title of the article")
    url: Annotated[str, HttpUrl] = Field(..., description="URL of the article")
    description: str = Field(..., description="Description of the article")
    date_published: datetime = Field(..., description="Publication date of the article")
    provider: str = Field(..., description="Provider of the article")
    origin_country: CountryAlpha2 = Field(..., description="Country of origin of the article.")
    image_url: Optional[Annotated[str, HttpUrl]] = Field(None, description="URL of the article's thumbnail image.")
    language: Optional[LanguageAlpha2] = Field(None, description="Language of the article.")
    source_api: str = Field(..., description="The name of the NewsSource class that fetched the article")