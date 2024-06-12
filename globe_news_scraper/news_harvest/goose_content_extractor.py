# Path: globe_news_scraper/news_harvest/goose_content_extractor.py

from goose3 import Goose, Article

from globe_news_scraper.models import GooseArticleClone


def extract_content(
        raw_html: str,
) -> GooseArticleClone:
    g = Goose()
    goose_article = g.extract(raw_html=raw_html)
    goose_article_prototype = GooseArticleClone(goose_article)
    return goose_article_prototype
