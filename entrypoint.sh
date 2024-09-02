#!/bin/bash

# Make sure the script fails on any command error
set -e

# Run database initialization
python -m globe_news_scraper.database.db_init --env ${SCRAPER_ENV:-prod}

# Start the main application
exec python main.py