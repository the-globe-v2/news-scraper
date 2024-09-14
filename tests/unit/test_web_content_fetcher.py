# path: tests/unit/test_web_content_fetcher.py

import pytest
from playwright.sync_api import TimeoutError, Error as PlaywrightError

from globe_news_scraper.data_providers.news_pipeline.web_content_fetcher import WebContentFetcher
from globe_news_scraper.monitoring.request_tracker import RequestTracker


@pytest.fixture
def web_content_fetcher(mock_config):
    request_tracker = RequestTracker()
    return WebContentFetcher(mock_config, request_tracker)


@pytest.mark.unit
def test_fetch_content_custom_domain_success(web_content_fetcher, mocker):
    mocker.patch.dict(web_content_fetcher._domain_fetchers,
                      {'example.com': mocker.Mock(return_value=(200, 'Custom content'))})
    content = web_content_fetcher.fetch_content('https://example.com')
    assert content == 'Custom content'
    assert web_content_fetcher._request_tracker.get_all_requests()['custom_example.com_request'][200] == 1


@pytest.mark.unit
def test_fetch_content_custom_domain_failure(web_content_fetcher, mocker):
    mocker.patch.dict(web_content_fetcher._domain_fetchers, {'example.com': mocker.Mock(return_value=(403, ''))})
    content = web_content_fetcher.fetch_content('https://example.com')
    assert content is None
    assert web_content_fetcher._request_tracker.get_all_requests()['custom_example.com_request'][403] == 1


@pytest.mark.unit
def test_fetch_content_basic_request_success(web_content_fetcher, mocker):
    mocker.patch.object(web_content_fetcher, '_fetch_with_requests', return_value=(200, 'Test content'))
    content = web_content_fetcher.fetch_content('https://example.com')
    assert content == 'Test content'
    assert web_content_fetcher._headers['User-Agent'] == 'RandomUserAgent'
    assert web_content_fetcher._request_tracker.get_all_requests()['basic_request'][200] == 1


@pytest.mark.unit
def test_fetch_content_postman_request_success(web_content_fetcher, mocker):
    mock_fetch = mocker.patch.object(web_content_fetcher, '_fetch_with_requests',
                                     side_effect=[(403, ''), (200, 'Postman content')])
    content = web_content_fetcher.fetch_content('https://example.com')
    _, kwargs = mock_fetch.call_args_list[1]
    assert content == 'Postman content'
    assert kwargs['headers']['User-Agent'] == 'MockPostmanAgent'
    assert web_content_fetcher._request_tracker.get_all_requests()['postman_request'][200] == 1


@pytest.mark.unit
def test_fetch_content_playwright_success(web_content_fetcher, mocker):
    mocker.patch.object(web_content_fetcher, '_fetch_with_requests', return_value=(403, ''))
    mocker.patch.object(web_content_fetcher, '_fetch_with_playwright', return_value=(200, 'Playwright content'))
    content = web_content_fetcher.fetch_content('https://example.com')
    assert content == 'Playwright content'
    assert web_content_fetcher._request_tracker.get_all_requests()['playwright_request'][200] == 1


@pytest.mark.unit
def test_fetch_content_all_methods_fail(web_content_fetcher, mocker):
    mocker.patch.object(web_content_fetcher, '_fetch_with_requests', return_value=(403, ''))
    mocker.patch.object(web_content_fetcher, '_fetch_with_playwright', return_value=(408, ''))
    content = web_content_fetcher.fetch_content('https://example.com')
    assert content is None
    assert web_content_fetcher._request_tracker.get_all_requests()['all_methods_failed'][408] == 1


@pytest.mark.unit
def test_logging_on_playwright_attempt(web_content_fetcher, mocker, log_output):
    mocker.patch.object(web_content_fetcher, '_fetch_with_requests', return_value=(403, None))
    mocker.patch.object(web_content_fetcher, '_fetch_with_playwright', return_value=(200, 'Playwright content'))
    web_content_fetcher.fetch_content('https://example.com')
    assert {'event': 'Failed to fetch https://example.com with "requests" library. Trying Playwright.',
            'log_level': 'debug'} in log_output.entries


@pytest.mark.unit
def test_logging_on_all_methods_fail(web_content_fetcher, mocker, log_output):
    mocker.patch.object(web_content_fetcher, '_fetch_with_requests', return_value=(403, None))
    mocker.patch.object(web_content_fetcher, '_fetch_with_playwright', return_value=(408, None))
    web_content_fetcher.fetch_content('https://example.com')
    assert {'event': 'All methods failed to load page: https://example.com', 'log_level': 'debug'} in log_output.entries


@pytest.fixture
def mock_playwright(mocker):
    mock_playwright = mocker.MagicMock()
    mock_playwright.__enter__.return_value = mock_playwright
    mock_playwright.firefox.launch.return_value = mocker.MagicMock()
    mock_playwright.firefox.launch.return_value.new_context.return_value = mocker.MagicMock()
    mock_playwright.firefox.launch.return_value.new_context.return_value.new_page.return_value = mocker.MagicMock()
    mocker.patch(
        "globe_news_scraper.data_providers.news_pipeline.web_content_fetcher.sync_playwright",
        return_value=mock_playwright,
    )
    return mock_playwright


def setup_msn_test(mock_playwright, status_code=200, content="<html><body>Custom MSN content</body></html>"):
    page = mock_playwright.firefox.launch.return_value.new_context.return_value.new_page.return_value
    page.goto.return_value.status = status_code
    page.evaluate.return_value = content
    return page


@pytest.mark.slow
def test_fetch_msn_com(web_content_fetcher, mock_playwright):
    page = setup_msn_test(mock_playwright)
    status_code, content = web_content_fetcher._fetch_msn_com("https://www.msn.com/article")

    assert status_code == 200
    assert content == "<html><body>Custom MSN content</body></html>"

    page.goto.assert_called_once_with("https://www.msn.com/article", timeout=10000)
    mock_playwright.firefox.launch.return_value.new_context.return_value.close.assert_called()
    mock_playwright.firefox.launch.return_value.close.assert_called()


@pytest.mark.unit
def test_fetch_msn_com_timeout(web_content_fetcher, mock_playwright, log_output):
    page = setup_msn_test(mock_playwright)
    page.goto.side_effect = TimeoutError("Timeout occurred")

    status_code, content = web_content_fetcher._fetch_msn_com("https://www.msn.com/article")

    assert status_code == 408
    assert content == ""
    assert log_output.entries[0] == {
        "event": "Failed to fetch article from MSN: Timeout exceeded for https://www.msn.com/article",
        "log_level": "warning",
    }


@pytest.mark.unit
def test_fetch_msn_com_error(web_content_fetcher, mock_playwright, log_output):
    page = setup_msn_test(mock_playwright)
    page.goto.side_effect = PlaywrightError("Unexpected Playwright error")

    status_code, content = web_content_fetcher._fetch_msn_com("https://www.msn.com/article")

    assert status_code == 500
    assert content == ""
    assert log_output.entries[0] == {
        "event": "MSN - Failed to fetch article content for "
                 "https://www.msn.com/article: Unexpected Playwright error",
        "log_level": "warning",
    }
