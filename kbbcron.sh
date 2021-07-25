#!/bin/sh
screen -h 1000 -L -Logfile kbb-cron-$$.log -dmS kbbcron -t kbb flock -n kbb.lock ./kbb.py
