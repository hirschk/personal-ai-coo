#!/usr/bin/env python3
"""
Sterl Session-End Nudge
Fires twice daily: 12:30pm EST (17:30 UTC) and 9:45pm EST (02:45 UTC)
Purpose: accountability check on today's outreach targets.
Silent if everything is actioned. Max 5 names.
"""

import json, os, sys, urllib.request, urllib.error
from datetime import datetime, timezone
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

WORKSPACE        = "/root/.openclaw/workspace"
TELEGRAM_TOKEN   = "8397276417:AAFelaU6_0xyF3ImUNmQ3TqW1erW4HieOY0"
TELEGRAM_CHAT_ID = "8768439197"
SHEET_ID         = "1o6XXLhpxFVZL5SlDKP8a56Y17brgmD7HWzAGe1Ei4Co"
GOG_TOKEN_FILE   = os.path.join(WORKSPACE, "config/gog-token.json")
CLIENT_SECRET    = os.path.join(WORKSPACE, "google_client_secret.json")
MAX_NAMES        = 5

TERMINAL_STATUS = {"replied", "meeting booked", "stale", "passed", "declined"}
SKIP_JOB_STATUS = {"removed", "paused", "applied", "screening", "interviewing",
                   "rejected", "passed", "hired", "declined"}
# "outreaching" intentionally excluded — stays active until referral confirmed


def sheets_client():
    with open(GOG_TOKEN_FILE) as f:
        tok = json.load(f)
    with open(CLIENT_SECRET) as f:
        secret = json.load(f)
    cfg = secret.get("installed") or secret.get("web") or secret
    creds = Credentials(
        token=tok.get("token"), refresh_token=tok["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=cfg["client_id"], client_secret=cfg["client_secret"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    if creds.expired or not creds.valid:
        creds.refresh(Request())
    return build("sheets", "v4", credentials=creds).spreadsheets()


def get_range(svc, r):
    try:
        return svc.values().get(spreadsheetId=SHEET_ID, range=r).execute().get("values", [])
    except Exception as e:
        print(f"[ERROR] get_range {r}: {e}", file=sys.stderr)
        return []


def pad(row, n):
    while len(row) < n:
        row.append("")
    return row


def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = json.dumps({
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status == 200
    except urllib.error.HTTPError as e:
        print(f"[ERROR] Telegram {e.code}: {e.read().decode()}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"[ERROR] Telegram: {e}", file=sys.stderr)
        return False


def main():
    today = datetime.now(timezone.utc).date()
    today_str = today.strftime("%Y-%m-%d")

    svc = sheets_client()

    outreach_rows  = get_range(svc, "Outreach!A2:H200")
    outreach_names = {pad(r, 2)[1].strip().lower() for r in outreach_rows if r}

    pending = []

    # Today's outreach rows not yet in terminal state
    for row in outreach_rows:
        row = pad(row, 8)
        date_str = row[0].strip()
        name     = row[1].strip()
        company  = row[2].strip()
        status   = row[5].strip().lower()

        if not name or date_str != today_str:
            continue
        if status in TERMINAL_STATUS:
            continue

        pending.append(f"{name} at {company}")

    # First contacts in Jobs not yet in Outreach at all
    job_rows = get_range(svc, "Jobs!A2:J200")
    for row in job_rows:
        row = pad(row, 10)
        company      = row[0].strip()
        network_path = row[7].strip()
        job_status   = row[8].strip().lower()

        if job_status in SKIP_JOB_STATUS or not network_path:
            continue

        contact = network_path.split("(")[0].strip()
        if contact.lower() in outreach_names:
            continue

        pending.append(f"{contact} at {company}")

    if not pending:
        print("All actioned. Silent.")
        return

    pending = pending[:MAX_NAMES]

    lines = ["<b>Before you close out:</b>", ""]
    for p in pending:
        lines.append(f"Did you message {p}?")
    lines.append("")
    lines.append("Just reply in plain language and I will update the sheet.")

    msg = "\n".join(lines)
    print(msg)
    send_telegram(msg)

if __name__ == "__main__":
    main()
