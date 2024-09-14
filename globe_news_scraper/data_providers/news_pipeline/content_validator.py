# path: globe_news_scraper/data_providers/content_validator.py

import html
import re
import unicodedata
from typing import List, Tuple, cast

from llm_guard.input_scanners import InvisibleText  # type: ignore[import-untyped]

from globe_news_scraper.config import Config


class ContentValidator:
    """
    A class for validating and sanitizing web content to ensure it meets certain criteria.

    This class checks for and sanitizes issues like gibberish content, unsafe patterns (e.g., scripts, iframes),
    and content length, and provides methods to sanitize content.
    """

    def __init__(self, config: Config):
        """
        Initialize the ContentValidator with configuration settings.

        :param config: Configuration object containing validation settings.
        """
        self._min_content_length = config.MIN_CONTENT_LENGTH
        self._max_content_length = config.MAX_CONTENT_LENGTH
        self._blocked_patterns = [
            r'<script.*?>.*?</script>',  # Match scripts
            r'<iframe.*?>.*?</iframe>',  # Match iframes
            r'(?<!\\)\'.*?(?<!\\)\'',  # Match single quotes
            r'(?<!\\)".*?(?<!\\)"',  # Match double quotes
            r'\$[a-zA-Z_][a-zA-Z0-9_]*',  # Match potential MongoDB operators
        ]

        self._invisible_text_sanitizer = InvisibleText()

    def validate(self, content: str) -> Tuple[bool, List[str]]:
        """
        Validate the content against various rules and patterns.

        This method checks the content length, looks for unsafe patterns,
        and detects potentially malicious code.

        :param content: The content to validate.
        :return: A tuple containing a boolean indicating if the content is valid and a list of issues found.
        """
        issues = []

        if self._max_content_length < len(content):
            issues.append(f"Content exceeds maximum length of {self._max_content_length} characters")
        elif len(content) < self._min_content_length:
            issues.append(f"Content does not meet minimum length of {self._min_content_length} characters")

        for pattern in self._blocked_patterns:
            if re.search(pattern, content, re.IGNORECASE | re.DOTALL):
                issues.append(f"Content contains potentially unsafe pattern: {pattern}")

        return len(issues) == 0, issues

    def sanitize(self, content: str) -> str:
        """
        Sanitize the content by removing or escaping potentially harmful content.

        This method removes unsafe patterns, HTML tags, normalizes newlines, and escapes special characters.

        :param content: The content to sanitize.
        :return: The sanitized content as a string.
        """
        # Remove or escape potentially harmful content
        for pattern in self._blocked_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.DOTALL)

        # Remove HTML tags (as an additional precaution)
        content = re.sub(r'<[^>]+>', '', content)

        # Normalize newlines
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        content = re.sub(r'\n{2,}', '\n', content)

        # Escape quotes and other special characters
        content = html.escape(content, quote=True)

        # Normalize unicode characters
        # https://unicode.org/reports/tr15/
        content = unicodedata.normalize('NFKC', content)

        # Remove invisible text
        content = self._sanitize_invisible_text(content)

        return content

    def _sanitize_invisible_text(self, content: str) -> str:
        """
        Sanitize the content by removing invisible text.

        :param content: The content to scan for gibberish.
        :return: The sanitized content as a string.
        """
        return cast(str, self._invisible_text_sanitizer.scan(content)[0])