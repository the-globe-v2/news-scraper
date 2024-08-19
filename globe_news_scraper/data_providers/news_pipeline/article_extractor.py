# Path: globe_news_scraper/data_providers/article_extractor.py
from typing import Optional, cast

from goose3 import Goose  # type: ignore[import-untyped]
from bs4 import BeautifulSoup, Comment
from pycountry import languages
from pydantic_extra_types.language_code import LanguageAlpha2

from globe_news_scraper.models import ArticleData


def extract_article(
        raw_html: str,
) -> ArticleData:
    g = Goose()
    goose_article = g.extract(raw_html=raw_html)

    try:
        meta_lang = _parse_language_code(goose_article.meta_lang)
    except ValueError:
        meta_lang = None

    article_data = ArticleData(
        cleaned_text=goose_article.cleaned_text,
        meta_lang=meta_lang,
        meta_keywords=goose_article.meta_keywords,
        authors=goose_article.authors,
        top_image=goose_article.top_image.src if goose_article.top_image else None,
    )

    # If the Goose extractor doesn't find any cleaned text, use an alternative method
    if len(article_data.cleaned_text) == 0:
        article_data.cleaned_text = _alternate_content_extraction(raw_html)

    return article_data


def _alternate_content_extraction(html_content: str) -> str:
    soup = BeautifulSoup(html_content, "lxml")

    # Remove comments
    for element in soup(text=lambda text: isinstance(text, Comment)):
        element.extract()

    # Remove script and style elements
    for script_or_style in soup(["script", "style"]):
        script_or_style.extract()

    # Remove all tags, leaving only the text content
    text_content = soup.get_text(separator=" ")

    # Clean and strip the text
    clean_text = ' '.join(text_content.split())

    return clean_text


def _parse_language_code(lang_code: str) -> Optional[LanguageAlpha2]:
    """
    Ensure that the provided language code is a valid LanguageAlpha2 code.
    """
    try:
        return cast(LanguageAlpha2, languages.get(alpha_2=lang_code).alpha_2)
    except KeyError:
        raise ValueError(f"Invalid language code: {lang_code}")
