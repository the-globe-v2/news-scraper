#!/bin/bash
# Start the cron service
cron -f &
# Run scraper in production
python /scraper/main.py --env prod
