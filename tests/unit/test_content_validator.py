# path: tests/unit/test_content_validator.py

import pytest

from globe_news_scraper.data_providers.news_pipeline.content_validator import (
    ContentValidator,
)


@pytest.mark.unit
def test_validate_content(mock_config):
    validator = ContentValidator(mock_config)

    valid_content = "This is a valid article content with sufficient length, which is configured to 100 chars in testing to pass the validation."
    is_valid, issues = validator.validate(valid_content)

    assert is_valid
    assert len(issues) == 0


@pytest.mark.unit
def test_validate_content_too_short(mock_config):
    validator = ContentValidator(mock_config)

    short_content = "Too short."
    is_valid, issues = validator.validate(short_content)

    assert not is_valid
    assert len(issues) == 1
    assert "Content does not meet minimum length" in issues[0]


@pytest.mark.unit
def test_unsafe_patterns_detection(mock_config):
    validator = ContentValidator(mock_config)

    unsafe_content = """<script>alert('XSS');</script>This is a valid article content with sufficient length, but with several unsafe patterns. $mongoOperator"""
    is_valid, issues = validator.validate(unsafe_content)

    assert not is_valid
    assert len(issues) == 3
    assert all("Content contains potentially unsafe pattern:" in issue for issue in issues)


@pytest.mark.unit
def test_sanitize_content(mock_config):
    validator = ContentValidator(mock_config)

    unsafe_content = "<script>alert('XSS');</script>Unsafe content with $mongoOperator Some\u200BInvisible\u200CText"
    sanitized_content = validator.sanitize(unsafe_content)

    assert "<script>" not in sanitized_content
    assert "alert('XSS');" not in sanitized_content
    assert "$mongoOperator" not in sanitized_content
    assert "\u200B" not in sanitized_content
    assert "Unsafe content with" in sanitized_content
