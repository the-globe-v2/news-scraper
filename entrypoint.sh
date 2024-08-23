#!/bin/bash
# Run scraper in production
python /scraper/main.py --env prod &
# Start the cron service
cron -f
