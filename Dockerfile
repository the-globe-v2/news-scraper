FROM python:3.11-slim

# Set the working directory for the application
WORKDIR /scraper

# Install Firefox ESR and necessary system packages
# Firefox ESR should pull in most necessary X and GTK libraries
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Install Playwright and Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install playwright \
    && playwright install firefox --with-deps  # Ensures necessary dependencies are installed

# Copy the application source code to the container
COPY . .

# Perform setup operations and adjust permissions
RUN python setup_database.py && \
    chmod +x main.py && \
    touch /var/log/cron.log

# Set up cron jobs by copying a crontab file into the correct directory and applying it
COPY crontab /etc/cron.d/scraper-crontab
RUN chmod 0644 /etc/cron.d/scraper-crontab && \
    crontab /etc/cron.d/scraper-crontab

# Environment variables can be defined
ENV NAME GlobeNewsScraper


# The container will run cron in the foreground to keep it alive
CMD ["sh", "-c", "cron && tail -f /var/log/cron.log"]
