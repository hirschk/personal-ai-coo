#!/usr/bin/env python3
"""
afternoon-checkin.py — 5:30pm EST daily check-in

Runs at 22:30 UTC via cron. Checks if there are unactioned jobs from
the morning brief AND fewer than 3 outreach messages sent today.
If both conditions are true, sends a nudge via Telegram.

Cron: 30 22 * * * python3 /root/.openclaw/workspace/scripts/afternoon-checkin.py >> /root/.openclaw/workspace/logs/afternoon-checkin.log 2>&1
"""

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv

WORKSPACE        = "/root/.openclaw/workspace"
SHEET_ID         = "1o6XXLhpxFVZL5SlDKP8a56Y17brgmD7HWzAGe1Ei4Co"
SA_KEY_FILE      = os.path.join(WORKSPACE, "config/sterl-sheets-key.json")
SHEETS_SCOPES    = ["https://www.googleapis.com/auth/spreadsheets"]
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


def sheets_client():
    try:
        creds = service_account.Credentials.from_service_account_file(
            SA_KEY_FILE, scopes=SHEETS_SCOPES
        )
        return build("sheets", "v4", credentials=creds).spreadsheets()
    except Exception as e:
        print(f"[checkin] ⚠ Sheets auth failed: {e}", file=sys.stderr)
        return None


def get_unactioned_jobs():
    """Load unactioned jobs from jobs-today.json cache. Falls back to Sheets if stale."""
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cache_path = os.path.join(WORKSPACE, "jobs-today.json")
    if os.path.exists(cache_path):
        try:
            with open(cache_path) as f:
                cache = json.load(f)
            if cache.get("timestamp", "")[:10] == today_str:
                # Get actioned companies from sheet (one small call)
                svc = sheets_client()
                actioned = set()
                if svc:
                    rows = svc.values().get(spreadsheetId=SHEET_ID,
                        range="Jobs!A2:I100").execute().get("values", [])
                    actioned = {r[0].lower() for r in rows if len(r) >= 9 and r[8].lower() != "new"}
                return [
                    {"company": j["company"], "role": j["title"]}
                    for j in cache.get("all_scored", cache.get("top_5", []))
                    if j["company"].lower() not in actioned
                ]
        except Exception as e:
            print(f"[checkin] cache read failed, falling back to Sheets: {e}")
    # Fallback: full Sheets read
    svc = sheets_client()
    if not svc: return []
    try:
        rows = svc.values().get(spreadsheetId=SHEET_ID, range="Jobs!A2:J100").execute().get("values", [])
        return [{"company": r[0], "role": r[1]} for r in rows
                if len(r) >= 9 and r[8].lower() == "new" and r[0] and r[1]]
    except Exception as e:
        print(f"[checkin] ⚠ Jobs fetch failed: {e}", file=sys.stderr)
        return []


def get_today_outreach_count():
    """Count outreach rows with status Sent/Replied/Meeting Booked dated today."""
    svc = sheets_client()
    if not svc:
        return 0
    try:
        result = svc.values().get(
            spreadsheetId=SHEET_ID,
            range="Outreach!A2:H100"
        ).execute()
        rows = result.get("values", [])
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        count = 0
        for row in rows:
            if len(row) < 6:
                continue
            date_str = row[0]
            status   = row[5] if len(row) > 5 else ""
            if date_str == today_str and status in ("Sent", "Replied", "Meeting Booked"):
                count += 1
        return count
    except Exception as e:
        print(f"[checkin] ⚠ Outreach count failed: {e}", file=sys.stderr)
        return 0


def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())


def main():
    now = datetime.now(timezone.utc)
    print(f"[{now.isoformat()}] Afternoon check-in starting")

    unactioned = get_unactioned_jobs()
    today_count = get_today_outreach_count()

    print(f"  Unactioned jobs: {len(unactioned)}")
    print(f"  Outreach sent today: {today_count}")

    # Only nudge if BOTH conditions are true
    if not unactioned:
        print("✅ No unactioned jobs — silent.")
        return 0

    if today_count >= 3:
        print(f"✅ {today_count} outreach sent today — target hit, silent.")
        return 0

    # Build message
    n = len(unactioned)
    lines = [
        f"👋 Afternoon check — you've got {n} unactioned job{'s' if n != 1 else ''} from this morning.\n",
    ]
    for i, job in enumerate(unactioned[:10], 1):
        lines.append(f"  {i}. *{job['role']}* @ {job['company']}")

    lines.append("\nSend a message today? Reply with a job number to draft outreach.")

    message = "\n".join(lines)
    print(f"  Sending nudge for {n} unactioned jobs...")
    send_telegram(message)
    print("✅ Afternoon check-in sent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
