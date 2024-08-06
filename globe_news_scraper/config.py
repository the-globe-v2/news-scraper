import os


class Config:
    """Base configuration class."""
    DEBUG = False
    TESTING = False
    LOG_LEVEL = "INFO"
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    BING_SEARCH_ENDPOINT = os.getenv("BING_SEARCH_ENDPOINT")
    BING_SEARCH_SUBSCRIPTION_KEY = os.getenv("BING_SEARCH_SUBSCRIPTION_KEY")

    # NEWS SCRAPING
    MAX_SCRAPING_WORKERS = 5  # Maximum number of concurrent scraping workers
    MINIMUM_CONTENT_LENGTH = 300  # Minimum length of article content to be considered valid
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.3",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 "
        "Safari/537.3",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 "
        "Safari/537.36 Edg/125.0.0.",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.3",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.3",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 "
        "Safari/537.36 Edg/123.0.0.",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 "
        "Safari/537.36 Edg/124.0.0.",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 "
        "Safari/537.36 Edg/117.0.2045.4",
        "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.",
        "Mozilla/5.0 (Windows NT 6.1; Trident/7.0; rv:11.0) like Geck",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.3",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 "
        "Safari/537.36 Edg/109.0.1518.5",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/118.",
        "Mozilla/5.0 (Windows NT 6.1; rv:109.0) Gecko/20100101 Firefox/115.",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/25.0 Chrome/121.0.0.0 "
        "Safari/537.3",
        "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/113.",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.3",
        "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/43.0.2357.65 Safari/537.3",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 "
        "Safari/537.36 Edg/122.0.0.",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.3",
        "Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Geck",
        "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.122 Safari/537.3",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 "
        "Safari/537.36 OPR/109.0.0."
    ]
    POSTMAN_USER_AGENT = "PostmanRuntime/7.39.0"

    HEADERS = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/",
        "Connection": "keep-alive"
    }


class DevelopmentConfig(Config):
    """Development configuration class."""

    DEBUG = True
    LOG_LEVEL = "DEBUG"
    LOGGING_DIR = "logs/dev"
    DATABASE_URI = os.getenv("DEV_DATABASE_URI")


class TestingConfig(Config):
    """Testing configuration class."""

    TESTING = True
    LOG_LEVEL = "DEBUG"
    DATABASE_URI = os.getenv("TEST_DATABASE_URI")


class ProductionConfig(Config):
    """Production configuration class."""

    DATABASE_URI = os.getenv("PROD_DATABASE_URI")
    LOG_LEVEL = "INFO"
    LOGGING_DIR = "logs"


def get_config(environment: str):
    """Retrieve and return the appropriate configuration class based on the environment."""
    if environment == "production":
        return ProductionConfig
    elif environment == "testing":
        return TestingConfig
    elif environment == "development":
        return DevelopmentConfig
    else:
        return Config
