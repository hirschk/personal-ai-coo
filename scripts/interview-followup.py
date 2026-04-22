#!/usr/bin/env python3
"""
Sterl Interview Follow-Up — event-driven via Google Calendar.

Runs every hour. Checks if any interview ended in the last 3 hours.
If found and no thank-you logged yet → fires thank-you draft to Telegram.
If no interview today → silent.

Cron: 0 * * * * python3 /root/.openclaw/workspace/scripts/interview-followup.py
"""

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build

SHEET_ID         = "1o6XXLhpxFVZL5SlDKP8a56Y17brgmD7HWzAGe1Ei4Co"
WORKSPACE        = "/root/.openclaw/workspace"
TELEGRAM_TOKEN   = "REDACTED"
TELEGRAM_CHAT_ID = "8768439197"
THANKYOU_LOG     = os.path.join(WORKSPACE, "logs/thankyou-sent.json")
SA_KEY_FILE      = os.path.join(WORKSPACE, "config/sterl-sheets-key.json")
SHEETS_SCOPES    = ["https://www.googleapis.com/auth/spreadsheets"]

INTERVIEW_KEYWORDS = [
    "interview", "screen", "call", "chat", "hiring", "recruiter",
    "product", "cpo", "cto", "vp ", "director", "manager"
]


def get_sheets_creds():
    # Service account — never expires
    return service_account.Credentials.from_service_account_file(
        SA_KEY_FILE, scopes=SHEETS_SCOPES
    )

# NOTE: Calendar access requires user OAuth (service accounts can't read personal calendars).
# Calendar checks are disabled until OAuth is re-authed. Sheets access is unaffected.


def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text,
               "parse_mode": "Markdown", "disable_web_page_preview": True}
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())


def load_thankyou_log():
    """Load log of thank-you prompts already sent (keyed by event ID or company+date)."""
    if not os.path.exists(THANKYOU_LOG):
        return {}
    with open(THANKYOU_LOG) as f:
        return json.load(f)


def save_thankyou_log(log):
    os.makedirs(os.path.dirname(THANKYOU_LOG), exist_ok=True)
    with open(THANKYOU_LOG, "w") as f:
        json.dump(log, f, indent=2)


def is_interview_event(title):
    """Check if a calendar event title looks like an interview."""
    t = title.lower()
    return any(kw in t for kw in INTERVIEW_KEYWORDS)


def get_interviews_from_sheet(svc_sheets):
    """Get interviews scheduled today from the Interviews sheet."""
    rows = svc_sheets.values().get(
        spreadsheetId=SHEET_ID, range="Interviews!A2:H100"
    ).execute().get("values", [])
    today = datetime.now(timezone.utc).date()
    interviews = []
    for row in rows:
        if len(row) < 5: continue
        company, role, stage, date_str, status = row[0], row[1], row[2], row[3], row[4]
        notes = row[5] if len(row) > 5 else ""
        if status in ("Complete", "Completed", "Passed", "Failed", "Thank-you Sent"):
            continue
        try:
            idate = datetime.strptime(date_str, "%Y-%m-%d").date()
            if idate == today:
                interviews.append({
                    "company": company, "role": role, "stage": stage,
                    "notes": notes, "date": date_str
                })
        except: pass
    return interviews


def get_recently_ended_calendar_events(svc_cal):
    """Get calendar events that ended in the last 3 hours."""
    now = datetime.now(timezone.utc)
    three_hours_ago = now - timedelta(hours=3)

    events = svc_cal.events().list(
        calendarId="primary",
        timeMin=three_hours_ago.isoformat(),
        timeMax=now.isoformat(),
        singleEvents=True,
        orderBy="startTime"
    ).execute()

    ended = []
    for e in events.get("items", []):
        end_str = e["end"].get("dateTime")
        if not end_str: continue
        end_dt = datetime.fromisoformat(end_str)
        if end_dt <= now:
            ended.append({
                "id": e["id"],
                "summary": e.get("summary", ""),
                "end": end_dt.isoformat()
            })
    return ended


def draft_thankyou(company, role, stage, notes):
    lines = [
        f"Hi [Name],\n",
        f"Thank you for taking the time to speak with me today about the {role} role at {company}.",
        f"I really enjoyed [specific thing discussed] — it reinforced why I'm excited about this opportunity.\n",
        f"[One relevant proof point from your background].",
        f"Looking forward to next steps.\n",
        f"Hirsch"
    ]
    return "\n".join(lines)


def main():
    now = datetime.now(timezone.utc)
    print(f"[{now.isoformat()}] interview-followup check starting")

    svc_sheets = build("sheets", "v4", credentials=get_sheets_creds()).spreadsheets()
    svc_cal    = None  # Calendar disabled until OAuth re-auth (service accounts can't read personal calendars)

    # Load what's already been sent
    sent_log = load_thankyou_log()

    # Get interviews from sheet (today's)
    sheet_interviews = get_interviews_from_sheet(svc_sheets)
    if not sheet_interviews:
        print("No interviews scheduled today in sheet. Silent.")
        return 0

    # Get calendar events that ended in last 3 hours
    recent_events = get_recently_ended_calendar_events(svc_cal)
    print(f"Recent ended calendar events: {[e['summary'] for e in recent_events]}")

    fired = 0
    for interview in sheet_interviews:
        company = interview["company"]
        log_key = f"{company}_{interview['date']}"

        # Already sent thank-you for this?
        if log_key in sent_log:
            print(f"  Already sent thank-you for {company}. Skipping.")
            continue

        # Check if a calendar event matching this company ended recently
        matched_event = None
        for event in recent_events:
            summary = event["summary"].lower()
            if company.lower() in summary or is_interview_event(summary):
                matched_event = event
                break

        if not matched_event:
            print(f"  No recent calendar event found for {company}. Waiting.")
            continue

        # Fire thank-you draft
        draft = draft_thankyou(
            interview["company"], interview["role"],
            interview["stage"], interview["notes"]
        )

        msg = (
            f"📬 *Thank-you note — {company}*\n"
            f"_{interview['role']} ({interview['stage']})_\n\n"
            f"Draft:\n```\n{draft}\n```\n"
            f"_Personalise the \\[brackets\\] and send. Reply 'sent {company}' when done._"
        )

        send_telegram(msg)
        print(f"  Sent thank-you prompt for {company}")

        # Log it
        sent_log[log_key] = now.isoformat()
        save_thankyou_log(sent_log)
        fired += 1

    if fired == 0:
        print("No interviews ended recently. Silent.")

    print(f"[{datetime.now(timezone.utc).isoformat()}] done — {fired} prompt(s) sent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
