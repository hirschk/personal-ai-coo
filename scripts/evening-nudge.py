#!/usr/bin/env python3
"""
Sterl Evening Nudge — 6pm EST daily (23:00 UTC)
Pings Hirsch if there are unactioned jobs or overdue outreach.
Silent if nothing needs attention.
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
TELEGRAM_TOKEN   = "REDACTED"
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

def main():
    svc = sheets_client()
    today = datetime.now(timezone.utc).date()

    # Unactioned jobs
    rows = svc.values().get(spreadsheetId=SHEET_ID, range="Jobs!A2:J100").execute().get("values", [])
    unactioned = []
    for row in rows:
        if len(row) < 9: continue
        company, role, status = row[0], row[1], row[8]
        score = row[4] if len(row) > 4 else ""
        url = row[3] if len(row) > 3 else ""
        if status.lower() == "new":
            unactioned.append({"company": company, "role": role, "score": score, "url": url})

    # Overdue outreach
    rows2 = svc.values().get(spreadsheetId=SHEET_ID, range="Outreach!A2:H100").execute().get("values", [])
    overdue = []
    for row in rows2:
        if len(row) < 6: continue
        date, name, company, channel, msg_type, status = row[0], row[1], row[2], row[3], row[4], row[5]
        if status in ("Replied", "Meeting Booked"): continue
        if status == "Sent" and date:
            try:
                sent = datetime.strptime(date, "%Y-%m-%d").date()
                if (today - sent).days >= 3:
                    overdue.append({"name": name, "company": company,
                                    "sent": date, "days_ago": (today - sent).days})
            except: pass

    # Nothing to do — stay silent
    if not unactioned and not overdue:
        print("Nothing to nudge. Silent.")
        return 0

    lines = ["🌆 *Evening check-in*\n"]

    if unactioned:
        lines.append(f"📥 *{len(unactioned)} job{'s' if len(unactioned) > 1 else ''} not yet actioned:*")
        for j in unactioned:
            line = f"  • *{j['role']}* @ {j['company']}"
            if j["score"]: line += f" (score {j['score']})"
            if j["url"]: line += f" — [View]({j['url']})"
            lines.append(line)

    if overdue:
        lines.append(f"\n🔔 *{len(overdue)} follow-up{'s' if len(overdue) > 1 else ''} overdue:*")
        for f in overdue:
            lines.append(f"  • *{f['name']}* @ {f['company']} — {f['days_ago']}d since last contact")

    lines.append("\n_Reply with a job number to draft outreach, or 'pass [num]' to skip it._")

    msg = "\n".join(lines)
    print(msg)
    send_telegram(msg)
    print("Sent.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
