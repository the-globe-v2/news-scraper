from pydantic import BaseModel, HttpUrl
from typing import Optional, List
from datetime import datetime

from goose3 import Article


class GlobeArticle(BaseModel):
    title: str
    description: str
    url: HttpUrl
    publication_date: datetime
    source: str
    language: str
    content: str
    keywords: List[str]
    category: Optional[str] = None
    authors: Optional[List[str]] = None
    summary: Optional[str] = None
    geographic_origin: Optional[str] = None
    geographic_connections: Optional[List[str]] = None
    image_url: Optional[HttpUrl] = None


class GooseArticleClone:
    def __init__(self, goose_article: Article):
        self.__dict__.update(goose_article.__dict__)

    def __setattr__(self, key, value):
        self.__dict__[key] = value
