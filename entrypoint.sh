#!/bin/sh
# Start the cron service
cron
# Run your main Python script
exec python /scraper/main.py --env prod
