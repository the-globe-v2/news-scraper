# path: globe_news_scraper/models.py

from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List
from datetime import datetime

from goose3 import Article

from globe_news_scraper.version import CURRENT_SCRAPER_VERSION


class GlobeArticle(BaseModel):
    title: str  # title of the article
    url: HttpUrl  # url of the article
    description: str  # description of the article
    date_published: datetime  # publication date of the article
    provider: str  # provider of the article
    language: str  # language of the article
    content: str  # main article body
    keywords: List[str] = Field(default=list())  # keywords associated with the article
    is_breaking_news: bool = Field(default=False)  # whether the article is breaking news
    scraper_version: str = Field(default=CURRENT_SCRAPER_VERSION)  # version of the scraper that fetched the article
    category: Optional[str] = Field(default=None)  # category of the article
    authors: Optional[List[str]] = Field(default=None)  # authors of the article
    summary: Optional[str] = Field(default=None)  # summary of the article
    geographic_origin: Optional[str] = Field(default=None)  # where the article originated from
    geographic_connections: Optional[List[str]] = Field(default=None)  # what countries the article is connected to
    image_url: Optional[HttpUrl] = Field(default=None)  # url of article header image
    trending_date: Optional[datetime] = Field(default=None)  # date the article was trending
    api_origin: Optional[str] = Field(default=None)  # which api the article originated from

    def update(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)


class MutableGooseArticle:
    """
        A mutable version of the goose3 Article class.

        This class inherits from Article but allows for modification of its attributes.
        It maintains the original immutable attributes while providing a mutable interface.
        """

    def __init__(self, *args, **kwargs):
        """
        Initialize the MutableGooseArticle.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        super().__init__(*args, **kwargs)
        # Dictionary to store mutable versions of attributes
        self._mutable_attributes = {}

    @classmethod
    def from_article(cls, article) -> 'MutableGooseArticle':
        """
        Create a MutableGooseArticle instance from an existing Article object.

        Args:
            article (Article): The original Article object to copy from.

        Returns:
            MutableGooseArticle: A new MutableGooseArticle instance with attributes copied from the original.
        """
        new_article = cls()
        for name in dir(article):
            if not name.startswith('_'):  # Skip private and special attributes
                try:
                    value = getattr(article, name)
                    setattr(new_article, name, value)
                except AttributeError:
                    pass  # Skip attributes that can't be read
        return new_article

    def __getattribute__(self, name):
        """
        Customize attribute access.

        This method first checks if the attribute has been modified (exists in _mutable_attributes).
        If so, it returns the modified value. Otherwise, it falls back to the original attribute.

        Args:
            name (str): The name of the attribute to access.

        Returns:
            The value of the attribute.
        """
        if name in object.__getattribute__(self, '_mutable_attributes'):
            return object.__getattribute__(self, '_mutable_attributes')[name]
        return super().__getattribute__(name)

    def __setattr__(self, name, value):
        """
        Customize attribute assignment.

        This method allows for setting new values for attributes, storing them in _mutable_attributes.

        Args:
            name (str): The name of the attribute to set.
            value: The value to assign to the attribute.
        """
        if name == '_mutable_attributes':
            # Directly set _mutable_attributes to avoid recursion
            object.__setattr__(self, name, value)
        else:
            # Store all other attributes in _mutable_attributes
            self._mutable_attributes[name] = value
