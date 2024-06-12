# Path: globe_news_scraper/news_harvest/goose_content_extractor.py

from goose3 import Goose, Article

from globe_news_scraper.models import GooseArticlePrototype


def extract_content(
        raw_html: str,
) -> GooseArticlePrototype:
    g = Goose()
    goose_article = g.extract(raw_html=raw_html)
    goose_article_prototype = GooseArticlePrototype(goose_article.__dict__)
    return goose_article_prototype
