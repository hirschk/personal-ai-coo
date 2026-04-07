#!/bin/bash
# Sterl Job Discovery Cron — Mon/Wed/Fri 11am EST
set -e

WORKSPACE="/root/.openclaw/workspace"
LOG="$WORKSPACE/logs/job-discovery.log"

echo "" >> "$LOG"
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] === Cron job discovery starting ===" >> "$LOG"

python3 "$WORKSPACE/scripts/job-discovery-apify.py" >> "$LOG" 2>&1

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] === Done ===" >> "$LOG"
