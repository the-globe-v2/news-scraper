# globe_news_scraper/data_providers/content_validator.py

import re
import html
import unicodedata
from typing import List, Tuple

from llm_guard.input_scanners import PromptInjection
from llm_guard.input_scanners.prompt_injection import MatchType

from globe_news_scraper.config import Config


class ContentValidator:
    def __init__(self, config: Config):
        self._min_content_length = config.MINIMUM_CONTENT_LENGTH
        self._max_content_length = config.MAX_CONTENT_LENGTH
        self._blocked_patterns = [
            r'<script.*?>.*?</script>',  # Match scripts
            r'<iframe.*?>.*?</iframe>',  # Match iframes
            r'(?<!\\)\'.*?(?<!\\)\'',  # Match single quotes
            r'(?<!\\)".*?(?<!\\)"',  # Match double quotes
            r'\$[a-zA-Z_][a-zA-Z0-9_]*',  # Match potential MongoDB operators
        ]

        # Initialize LLM prompt scanners
        # In my testing this match type catches enough prompt injections without taking too long
        # It is not perfect but from my testing, if a prompt injection is makes it past this scanner
        # it also doesn't affect the output of the model. CHUNKS and SENTENCE match types are more accurate
        self._prompt_injection_scanner = PromptInjection(threshold=0.5, match_type=MatchType.TRUNCATE_TOKEN_HEAD_TAIL)

    def validate(self, content: str) -> Tuple[bool, List[str]]:
        issues = []

        if self._max_content_length < len(content):
            issues.append(f"Content exceeds maximum length of {self._max_content_length} characters")
        elif len(content) < self._min_content_length:
            issues.append(f"Content does not meet minimum length of {self._min_content_length} characters")

        for pattern in self._blocked_patterns:
            if re.search(pattern, content, re.IGNORECASE | re.DOTALL):
                issues.append(f"Content contains potentially unsafe pattern: {pattern}")

        return len(issues) == 0, issues

    def _detect_prompt_injection(self, content: str) -> bool:
        return self._prompt_injection_scanner.scan(content)[1]

    def sanitize(self, content: str) -> str:
        # Remove or escape potentially harmful content
        for pattern in self._blocked_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.DOTALL)

        # Remove HTML tags, this is likely NOT necessary due to gooses parser, but it's here just in case
        content = re.sub(r'<[^>]+>', '', content)

        # Normalize newlines
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        content = re.sub(r'\n{2,}', '\n', content)

        # Escape quotes and other special characters
        content = html.escape(content, quote=True)

        # Normalize unicode characters
        # https://unicode.org/reports/tr15/
        content = unicodedata.normalize('NFKC', content)

        return content
