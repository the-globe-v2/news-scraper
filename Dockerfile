FROM python:3.12-slim

# Set the working directory for the application
WORKDIR /scraper

# Install Firefox ESR, necessary system packages, and build tools
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    firefox-esr \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Playwright and Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install playwright \
    && playwright install firefox --with-deps

# Copy the application source code to the container
COPY . .

# Adjust permissions for the main script
RUN chmod +x main.py

# Environment variables can be defined here or overridden at runtime
ENV SCRAPER_ENV=prod
ENV SCRAPER_LOG_LEVEL=INFO
ENV SCRAPER_CRON_SCHEDULE="0 2 * * *"
ENV SCRAPER_RUN_NOW=false

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]