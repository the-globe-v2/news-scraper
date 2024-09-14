# path: tests/conftest.py

import pytest
import structlog
from structlog.testing import LogCapture

from globe_news_scraper.config import Config
from globe_news_scraper.monitoring import GlobeScraperTelemetry


@pytest.fixture
def mock_config():
    return Config(
        ENV='test',
        LOG_LEVEL='debug',
        LOGGING_DIR='./test_logs',
        BING_SEARCH_ENDPOINT='https://api.bing.microsoft.com/v7.0/news',
        BING_SEARCH_SUBSCRIPTION_KEY='mock_key',
        BING_SEARCH_COUNTRIES=['de-DE', 'es-ES'],
        MONGO_URI='mongodb://localhost:27017',
        MONGO_DB='test_db',
        MAX_SCRAPING_WORKERS=2,
        MIN_CONTENT_LENGTH=100,
        MAX_CONTENT_LENGTH=10000,
        USER_AGENTS=['RandomUserAgent'],
        POSTMAN_USER_AGENT='MockPostmanAgent'
    )


@pytest.fixture
def mock_telemetry():
    return GlobeScraperTelemetry()


@pytest.fixture(name="log_output")
def fixture_log_output():
    return LogCapture()


@pytest.fixture(autouse=True)
def fixture_configure_structlog(log_output):
    structlog.configure(
        processors=[log_output]
    )
    yield
    # Reset configuration after each test
    structlog.reset_defaults()


@pytest.fixture
def capturing_logger_factory():
    return structlog.testing.CapturingLoggerFactory()


@pytest.fixture
def sample_news_article_html():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Sample News Article</title>
    </head>
    <body>
        <header>
            <h1>Breaking News: Major Discovery in Renewable Energy</h1>
            <p class="byline">By Jane Doe, Science Reporter</p>
            <p class="date">June 25, 2023</p>
        </header>
        <article>
            <p>In a groundbreaking development, researchers at Tech Innovations Lab have unveiled a new technology that promises to significantly enhance the efficiency of solar panels. The technology, which has been in development for over five years, could revolutionize the renewable energy sector.</p>
            <p>This new method involves a special coating that increases light absorption and reduces energy loss, making solar panels up to 30% more efficient than current models. The implications for both commercial and residential energy use are profound, offering a more sustainable and cost-effective energy solution.</p>
            <p>The team behind the discovery is planning a series of tests to further refine the technology before it hits the market. Experts predict that this innovation could lead to wider adoption of solar energy, potentially reducing reliance on fossil fuels and contributing to global efforts against climate change.</p>
        </article>
        <footer>
            <p>Contact us at <a href="mailto:editor@example.com">editor@example.com</a> for more information.</p>
        </footer>
    </body>
    </html>
    """


@pytest.fixture
def sample_short_article_html():
    return """
    <html lang="en">
    <head>
        <title>Short News Article</title>
    </head>
    <body>
        <header>
            <h1>Breaking News: Major Discovery in Renewable Energy</h1>
            <p class="date">June 25, 2023</p>
        </header>
        <article>
            <p>In a groundbreaking development, researchers at Tech Innovations Lab have unveiled nothing.</p>
        </article>
        <footer>
            <p>Contact us at <a href="mailto:editor@example.com">editor@example.com</a> for more information.</p>
        </footer>
    </body>
    </html>
    """
