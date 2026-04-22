#!/usr/bin/env python3
"""
ideas-capture.py — Domain 3: Ideas OS
Capture a raw idea, log it, sheet it, queue it for structuring.
Usage: python3 ideas-capture.py "your idea here"
       echo "your idea here" | python3 ideas-capture.py
"""

import sys
import os
import json
import datetime
import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build

WORKSPACE = "/root/.openclaw/workspace"
SHEET_ID = "1o6XXLhpxFVZL5SlDKP8a56Y17brgmD7HWzAGe1Ei4Co"
IDEAS_TAB = "Ideas"
PENDING_FILE = os.path.join(WORKSPACE, "ideas-pending.json")
LOG_FILE = os.path.join(WORKSPACE, "logs/ideas.log")
TELEGRAM_BOT = "REDACTED"
TELEGRAM_CHAT = "8768439197"

HEADERS = ["Idea", "Status", "First Step", "Due Date", "Last Update", "Notes"]


def log(msg):
    print(msg)
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(msg + "\n")


SA_KEY_FILE = os.path.join(WORKSPACE, "config/sterl-sheets-key.json")
SHEETS_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def get_creds():
    return service_account.Credentials.from_service_account_file(
        SA_KEY_FILE, scopes=SHEETS_SCOPES
    )


def ensure_ideas_tab(service):
    """Create Ideas tab with headers if it doesn't exist."""
    meta = service.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
    existing = [s["properties"]["title"] for s in meta["sheets"]]
    if IDEAS_TAB not in existing:
        log(f"[ideas-capture] Creating '{IDEAS_TAB}' tab...")
        body = {
            "requests": [
                {
                    "addSheet": {
                        "properties": {"title": IDEAS_TAB}
                    }
                }
            ]
        }
        service.spreadsheets().batchUpdate(
            spreadsheetId=SHEET_ID, body=body
        ).execute()
        # Write headers
        service.spreadsheets().values().update(
            spreadsheetId=SHEET_ID,
            range=f"{IDEAS_TAB}!A1:F1",
            valueInputOption="RAW",
            body={"values": [HEADERS]},
        ).execute()
        log(f"[ideas-capture] '{IDEAS_TAB}' tab created with headers.")
    else:
        log(f"[ideas-capture] '{IDEAS_TAB}' tab already exists.")


def append_to_sheet(service, idea_text, now_str):
    """Append a new row to the Ideas sheet."""
    row = [idea_text, "Captured", "", "", now_str, ""]
    service.spreadsheets().values().append(
        spreadsheetId=SHEET_ID,
        range=f"{IDEAS_TAB}!A:F",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": [row]},
    ).execute()
    log(f"[ideas-capture] Appended to sheet.")


def save_pending(idea_text, now_str):
    """Append idea to ideas-pending.json for later structuring."""
    pending = []
    if os.path.exists(PENDING_FILE):
        with open(PENDING_FILE) as f:
            try:
                pending = json.load(f)
            except json.JSONDecodeError:
                pending = []
    entry = {
        "idea": idea_text,
        "captured_at": now_str,
        "structured": False,
    }
    pending.append(entry)
    with open(PENDING_FILE, "w") as f:
        json.dump(pending, f, indent=2)
    log(f"[ideas-capture] Saved to ideas-pending.json ({len(pending)} total pending).")


def send_telegram(text):
    """Send a Telegram message."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT}/sendMessage"
    resp = requests.post(url, json={"chat_id": TELEGRAM_CHAT, "text": text}, timeout=10)
    if resp.status_code != 200:
        log(f"[ideas-capture] Telegram error: {resp.text}")
    else:
        log(f"[ideas-capture] Telegram ack sent.")


def main():
    # Get idea text from arg or stdin
    if len(sys.argv) > 1:
        idea_text = " ".join(sys.argv[1:]).strip()
    elif not sys.stdin.isatty():
        idea_text = sys.stdin.read().strip()
    else:
        print("Usage: python3 ideas-capture.py \"your idea here\"")
        sys.exit(1)

    if not idea_text:
        print("Error: empty idea.")
        sys.exit(1)

    now = datetime.datetime.utcnow()
    now_str = now.strftime("%Y-%m-%d %H:%M UTC")

    log(f"\n[{now_str}] [ideas-capture] New idea: {idea_text}")

    # Google Sheets
    creds = get_creds()
    service = build("sheets", "v4", credentials=creds)
    ensure_ideas_tab(service)
    append_to_sheet(service, idea_text, now_str)

    # Local pending queue
    save_pending(idea_text, now_str)

    # Telegram ack
    send_telegram("Got it, logged. 💡 I'll structure it tonight.")

    log(f"[ideas-capture] Done.")


if __name__ == "__main__":
    main()
