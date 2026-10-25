#!/usr/bin/env bash
# Daily 8h mining window with in-window crash recovery.
# systemd starts this once per day (twitch-miner-daily.timer); the loop keeps the
# miner alive for 8 hours and stops early if it exits cleanly (e.g. session invalid).
set -u

cd "$(dirname "$0")" || exit 1
PY=env/bin/python
BUDGET=$((8 * 3600))
START=$(date +%s)
END=$((START + BUDGET))
ATTEMPTS=0

while [ "$(date +%s)" -lt "$END" ]; do
    ATTEMPTS=$((ATTEMPTS + 1))
    if [ "$ATTEMPTS" -gt 20 ]; then
        echo "daily_window: too many restarts ($ATTEMPTS), giving up for today"
        exit 1
    fi
    "$PY" run_headless.py
    rc=$?
    if [ "$rc" -eq 0 ]; then
        echo "daily_window: miner exited cleanly (rc=0), stopping window"
        exit 0
    fi
    if [ "$rc" -eq 2 ]; then
        echo "daily_window: no token (rc=2); needs smartbox_login.py — stopping"
        exit 2
    fi
    remaining=$((END - $(date +%s)))
    echo "daily_window: miner rc=$rc, restarting in 30s (remaining ${remaining}s)"
    sleep 30
done

echo "daily_window: 8h window complete"
exit 0
