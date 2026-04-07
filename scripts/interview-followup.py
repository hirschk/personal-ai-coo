#!/usr/bin/env python3
"""
Sterl Interview Follow-Up — runs 2 hours after typical interview window.
Checks for interviews scheduled today, reminds Hirsch to send thank-you notes.
Also re-fires at +24h if not yet sent.
"""

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone, timedelta
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SHEET_ID         = "1o6XXLhpxFVZL5SlDKP8a56Y17brgmD7HWzAGe1Ei4Co"
WORKSPACE        = "/root/.openclaw/workspace"
TELEGRAM_TOKEN   = "8397276417:AAFelaU6_0xyF3ImUNmQ3TqW1erW4HieOY0"
TELEGRAM_CHAT_ID = "8768439197"

def sheets_client():
    with open(os.path.join(WORKSPACE, "config/gog-token.json")) as f:
        tok = json.load(f)
    with open(os.path.join(WORKSPACE, "google_client_secret.json")) as f:
        secret = json.load(f)
    cfg = secret.get("installed") or secret.get("web") or secret
    creds = Credentials(
        token=None, refresh_token=tok["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=cfg["client_id"], client_secret=cfg["client_secret"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    return build("sheets", "v4", credentials=creds).spreadsheets()

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text,
               "parse_mode": "Markdown", "disable_web_page_preview": True}
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())

def draft_thankyou(company, role, stage, notes):
    """Generate a thank-you note template."""
    return (
        f"Hi [Name],\n\n"
        f"Thank you for taking the time to speak with me today about the {role} role at {company}. "
        f"I really enjoyed learning more about [specific thing discussed] — "
        f"it reinforced why I'm excited about this opportunity.\n\n"
        f"As I mentioned, [one relevant proof point from your background]. "
        f"I'd love to continue the conversation.\n\n"
        f"Looking forward to next steps.\n\nHirsch"
    )

def main():
    svc = sheets_client()
    today = datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)

    rows = svc.values().get(
        spreadsheetId=SHEET_ID, range="Interviews!A2:H100"
    ).execute().get("values", [])

    to_remind = []
    for row in rows:
        if len(row) < 5: continue
        company, role, stage, date_str, status = row[0], row[1], row[2], row[3], row[4]
        notes = row[5] if len(row) > 5 else ""
        next_action = row[6] if len(row) > 6 else ""

        if status in ("Completed", "Passed", "Failed"):
            continue

        try:
            idate = datetime.strptime(date_str, "%Y-%m-%d").date()
        except:
            continue

        # Today's interviews — 2-hour reminder
        if idate == today and status in ("Pending", "Scheduled"):
            to_remind.append({
                "company": company, "role": role, "stage": stage,
                "notes": notes, "urgency": "today"
            })
        # Yesterday's interviews — 24-hour follow-up if no thank-you sent
        elif idate == yesterday and status in ("Pending", "Scheduled"):
            to_remind.append({
                "company": company, "role": role, "stage": stage,
                "notes": notes, "urgency": "overdue"
            })

    if not to_remind:
        print("No interviews to follow up on. Silent.")
        return 0

    lines = []
    for iv in to_remind:
        if iv["urgency"] == "today":
            lines.append(f"📬 *Thank-you note — {iv['company']}*")
            lines.append(f"_{iv['role']} ({iv['stage']})_\n")
            lines.append("Draft:\n```")
            lines.append(draft_thankyou(iv["company"], iv["role"], iv["stage"], iv["notes"]))
            lines.append("```")
            lines.append("_Personalise the [brackets] and send. Reply 'sent [company]' when done._\n")
        else:
            lines.append(f"⚠️ *24h passed — did you send a thank-you to {iv['company']}?*")
            lines.append(f"_{iv['role']} ({iv['stage']})_")
            lines.append("_Reply 'sent [company]' to mark done, or I'll keep reminding._\n")

    msg = "\n".join(lines)
    print(msg)
    send_telegram(msg)
    print("Sent.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
