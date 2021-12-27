#!/bin/sh
screen -h 1000 -L -Logfile "log/cron-$(date +%y%m%d-%H%M%S).log" -dmS kbbcron -t kbb flock -n kbb.lock ./kbb.py
