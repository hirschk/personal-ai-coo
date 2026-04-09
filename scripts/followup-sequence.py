#!/usr/bin/env python3
"""
followup-sequence.py -- Daily outreach follow-up reminder

Runs daily at 14:30 UTC (9:30am EST) via cron.

Follow-up cadence (days from LAST TOUCH, column A):
  D3  -> 3 days after last touch
  D7  -> 7 days after last touch
  D14 -> 7 days after last touch (i.e. 7 days after D7)

When a stage fires, column A is updated to today so the NEXT interval
is measured from the actual follow-up date, not the original send date.

Sheet columns (Outreach!A2:H):
  A: Date     (YYYY-MM-DD -- updated to today on each follow-up fire)
  B: Name
  C: Company
  D: Channel
  E: Type
  F: Status   (Sent / Replied / Meeting Booked / Stale)
  G: FollowUp (current stage: D3 / D7 / D14)
  H: Notes
"""

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone, timedelta

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

WORKSPACE        = "/root/.openclaw/workspace"
TELEGRAM_TOKEN   = "8397276417:AAFelaU6_0xyFz3ImUNmQ3TqW1erW4HieOY0"
TELEGRAM_CHAT_ID = "8768439197"
SHEET_ID         = "1o6XXLhpxFVZL5SlDKP8a56Y17brgmD7HWzAGe1Ei4Co"
SHEET_RANGE      = "Outreach!A2:H200"
TASKS_RANGE      = "Tasks!A2:F200"
GOG_TOKEN_FILE   = os.path.join(WORKSPACE, "config/gog-token.json")
CLIENT_SECRET    = os.path.join(WORKSPACE, "google_client_secret.json")

COL_DATE     = 0
COL_NAME     = 1
COL_COMPANY  = 2
COL_CHANNEL  = 3
COL_TYPE     = 4
COL_STATUS   = 5
COL_FOLLOWUP = 6
COL_NOTES    = 7

TASK_COL_ID      = 0
TASK_COL_NAME    = 1
TASK_COL_PROJECT = 2
TASK_COL_STATUS  = 3
TASK_COL_DUE     = 4
TASK_COL_NOTES   = 5

STAGE_ORDER = ["D3", "D7", "D14"]
STAGE_DAYS  = {"D3": 3, "D7": 7, "D14": 7}
SKIP_STATUSES = {"replied", "meeting booked", "stale"}


def sheets_client():
    try:
        with open(GOG_TOKEN_FILE) as f:
            tok = json.load(f)
        with open(CLIENT_SECRET) as f:
            secret = json.load(f)
        cfg = secret.get("installed") or secret.get("web") or secret
        creds = Credentials(
            token=tok.get("token"),
            refresh_token=tok["refresh_token"],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=cfg["client_id"],
            client_secret=cfg["client_secret"],
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        if creds.expired or not creds.valid:
            creds.refresh(Request())
        return build("sheets", "v4", credentials=creds).spreadsheets()
    except Exception as e:
        print(f"[ERROR] Sheets auth failed: {e}", file=sys.stderr)
        return None


def load_outreach_rows(svc):
    try:
        result = svc.values().get(spreadsheetId=SHEET_ID, range=SHEET_RANGE).execute()
        return result.get("values", [])
    except Exception as e:
        print(f"[ERROR] Could not load Outreach sheet: {e}", file=sys.stderr)
        return []


def load_tasks_due_today(svc):
    try:
        result = svc.values().get(spreadsheetId=SHEET_ID, range=TASKS_RANGE).execute()
        rows = result.get("values", [])
    except Exception as e:
        print(f"[ERROR] Could not load Tasks sheet: {e}", file=sys.stderr)
        return []

    today = datetime.now(timezone.utc).date()
    due = []
    for row in rows:
        while len(row) < 6:
            row.append("")
        task_status = row[TASK_COL_STATUS].strip().lower()
        if task_status in ("done", "cancelled", "complete"):
            continue
        due_str = row[TASK_COL_DUE].strip()
        if not due_str:
            continue
        try:
            due_date = datetime.strptime(due_str, "%Y-%m-%d").date()
        except ValueError:
            continue
        if due_date <= today:
            due.append(row)
    return due


def next_stage(current_stage):
    if not current_stage or current_stage not in STAGE_ORDER:
        return None
    idx = STAGE_ORDER.index(current_stage)
    if idx + 1 < len(STAGE_ORDER):
        return STAGE_ORDER[idx + 1]
    return None


def update_row(svc, row_index, date_str, followup_stage):
    """Update columns A (date) and G (followup stage) for a given data row.
    row_index is 0-based relative to SHEET_RANGE start (row 2 in sheet = index 0)."""
    sheet_row = row_index + 2  # +2 because data starts at row 2, index is 0-based
    updates = [
        {
            "range": f"Outreach!A{sheet_row}",
            "values": [[date_str]],
        },
        {
            "range": f"Outreach!G{sheet_row}",
            "values": [[followup_stage]],
        },
    ]
    body = {
        "valueInputOption": "USER_ENTERED",
        "data": updates,
    }
    try:
        svc.values().batchUpdate(spreadsheetId=SHEET_ID, body=body).execute()
    except Exception as e:
        print(f"[ERROR] Could not update row {sheet_row}: {e}", file=sys.stderr)


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = json.dumps({
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
    }).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"[ERROR] Telegram send failed: {e}", file=sys.stderr)
        return False


def main():
    today = datetime.now(timezone.utc).date()
    today_str = today.strftime("%Y-%m-%d")

    svc = sheets_client()
    if svc is None:
        print("[ERROR] Could not create Sheets client. Exiting.", file=sys.stderr)
        sys.exit(1)

    # -----------------------------------------------------------------------
    # Outreach follow-ups
    # -----------------------------------------------------------------------
    rows = load_outreach_rows(svc)
    follow_ups = []

    for i, row in enumerate(rows):
        while len(row) < 8:
            row.append("")

        status    = row[COL_STATUS].strip().lower()
        followup  = row[COL_FOLLOWUP].strip()
        date_str  = row[COL_DATE].strip()
        name      = row[COL_NAME].strip()
        company   = row[COL_COMPANY].strip()
        channel   = row[COL_CHANNEL].strip()

        # Skip terminal statuses
        if status in SKIP_STATUSES:
            continue

        # Skip rows with no active follow-up stage
        if not followup or followup not in STAGE_ORDER:
            continue

        # Skip rows with no date
        if not date_str:
            continue

        try:
            last_touch = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            continue

        days_since = (today - last_touch).days
        required_days = STAGE_DAYS[followup]

        if days_since >= required_days:
            follow_ups.append((i, name, company, channel, followup, row))
            # Advance to next stage (or clear if D14 done)
            new_stage = next_stage(followup)
            update_row(svc, i, today_str, new_stage if new_stage else "Done")

    # -----------------------------------------------------------------------
    # Tasks due today
    # -----------------------------------------------------------------------
    tasks_due = load_tasks_due_today(svc)

    # -----------------------------------------------------------------------
    # Build and send Telegram message
    # -----------------------------------------------------------------------
    if not follow_ups and not tasks_due:
        print("[INFO] Nothing to report today.")
        return

    lines = [f"*Daily Outreach Check-In* — {today_str}\n"]

    if follow_ups:
        lines.append(f"*{len(follow_ups)} follow-up(s) due:*")
        for (_, name, company, channel, stage, _row) in follow_ups:
            label = f"{name} @ {company}" if company else name
            lines.append(f"  • [{stage}] {label} via {channel}")
        lines.append("")

    if tasks_due:
        lines.append(f"*{len(tasks_due)} task(s) overdue or due today:*")
        for row in tasks_due:
            task_name    = row[TASK_COL_NAME].strip()
            task_project = row[TASK_COL_PROJECT].strip()
            task_due     = row[TASK_COL_DUE].strip()
            label = f"{task_name} ({task_project})" if task_project else task_name
            lines.append(f"  • {label} — due {task_due}")

    message = "\n".join(lines)
    print(message)
    send_telegram(message)


if __name__ == "__main__":
    main()
