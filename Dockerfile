FROM python:3.11-slim

WORKDIR /scraper

# Install necessary packages and clean up in one layer
RUN apt-get update && apt-get install -y \
    cron \
    firefox-esr \
    && rm -rf /var/lib/apt/lists/*

# Create a user and group with specific IDs
RUN addgroup --system scraper && adduser --system --ingroup scraper scraper

# Copy only the necessary files and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Set up the environment
RUN python setup_database.py && \
    chmod +x main.py && \
    touch /var/log/cron.log && \
    chmod 0644 /etc/cron.d/scraper-crontab && \
    crontab /etc/cron.d/scraper-crontab

# Change ownership of the working directory
RUN chown -R scraper:scraper /scraper

# Switch to the non-root user
USER scraper

ENV NAME GlobeNewsScraper
ENV ENV=prod

# Start cron in the foreground
CMD ["cron", "-f"]
