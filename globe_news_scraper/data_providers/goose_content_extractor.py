# Path: globe_news_scraper/data_providers/goose_content_extractor.py

from goose3 import Goose # type: ignore[import-untyped]

from globe_news_scraper.models import MutableGooseArticle


def extract_content(
        raw_html: str,
) -> MutableGooseArticle:
    g = Goose()
    goose_article = g.extract(raw_html=raw_html)
    mutable_goose_article = MutableGooseArticle.from_article(goose_article)
    return mutable_goose_article
