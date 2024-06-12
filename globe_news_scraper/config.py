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
    MINIMUM_CONTENT_LENGTH = (
        50  # Minimum length of article content to be considered valid
    )
    USER_AGENTS = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 "
                   "Safari/537.36")

    HEADERS = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Cache-Control": "no-cache",
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
