FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /scraper

# Install system dependencies including cron
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    cron \
    firefox-esr \
    && rm -rf /var/lib/apt/lists/*

# Copy the current directory contents into the container at /scraper
COPY . /scraper

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install firefox

# Make main.py script executable
RUN chmod +x /scraper/main.py

# Add crontab file in the cron directory
COPY crontab /etc/cron.d/scraper-crontab

# Give execution rights on the cron job
RUN chmod 0644 /etc/cron.d/scraper-crontab

# Apply cron job
RUN crontab /etc/cron.d/scraper-crontab

# Create the log file to be able to run tail
RUN touch /var/log/cron.log

# Define environment variable
ENV NAME GlobeNewsScraper

# Set the default environment to 'prod'
ENV ENV=prod

# Run setup_database.py when the container launches
RUN python setup_database.py

# Use a shell script to start both cron and the main Python script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
CMD ["/entrypoint.sh"]
