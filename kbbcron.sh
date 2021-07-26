#!/bin/sh
screen -h 1000 -L -Logfile "log/kbb-cron-$(date +%y%m%d)-$$.log" -dmS kbbcron -t kbb flock -n kbb.lock ./kbb.py
