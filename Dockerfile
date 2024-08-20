# Use an official Python runtime as a parent image
FROM python:3.11-slim
LABEL authors="s.martinez-avial"

# Set the working directory in the container
WORKDIR /scraper

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Firefox and dependencies for Playwright
RUN apt-get update && apt-get install -y \
    firefox-esr \
    && rm -rf /var/lib/apt/lists/*

# Copy the current directory contents into the container at /scraper
COPY . /scraper

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install firefox

# Define environment variable
ENV NAME GlobeNewsScraper

# Run setup_database.py when the container launches
RUN python setup_database.py

# Run main.py when the container launches
CMD ["python", "main.py", "--env", "prod"]