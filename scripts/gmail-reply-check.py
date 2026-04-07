#!/usr/bin/env python3
"""
Sterl Gmail Reply Detection — runs every 2 hours via cron.

What it does:
1. Pulls all "Sent" rows from the Outreach sheet (Status != Replied/cold)
2. Searches Gmail inbox for unread messages from those people
3. For any match: updates Status to "Replied" in the sheet
4. Sends Telegram notification: "🟢 Reply from [Name] @ [Company] — check your inbox"

Cron: 0 */2 * * * /usr/bin/python3 /root/.openclaw/workspace/scripts/gmail-reply-check.py
"""

import base64
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# ─── Config ───────────────────────────────────────────────────────────────────

WORKSPACE        = "/root/.openclaw/workspace"
SHEET_ID         = "1o6XXLhpxFVZL5SlDKP8a56Y17brgmD7HWzAGe1Ei4Co"
SHEET_RANGE      = "Outreach!A2:H100"
TELEGRAM_TOKEN   = "8397276417:AAFelaU6_0xyF3ImUNmQ3TqW1erW4HieOY0"
TELEGRAM_CHAT_ID = "8768439197"

# Outreach sheet columns (0-indexed):
# 0=Date, 1=Name, 2=Company, 3=Channel, 4=Type, 5=Status, 6=FollowUp, 7=Notes
COL_DATE    = 0
COL_NAME    = 1
COL_COMPANY = 2
COL_STATUS  = 5

# Statuses that mean we're still waiting for a reply
ACTIVE_STATUSES = {"sent", "followed up", "pending", "no reply", ""}


# ─── Auth ─────────────────────────────────────────────────────────────────────

def get_credentials(scopes):
    token_path  = os.path.join(WORKSPACE, "config/gog-token.json")
    secret_path = os.path.join(WORKSPACE, "google_client_secret.json")
    with open(token_path) as f:
        tok = json.load(f)
    with open(secret_path) as f:
        secret = json.load(f)
    cfg = secret.get("installed") or secret.get("web") or secret
    return Credentials(
        token=None,
        refresh_token=tok["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=cfg["client_id"],
        client_secret=cfg["client_secret"],
        scopes=scopes,
    )


def gmail_client():
    creds = get_credentials([
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.modify",
    ])
    return build("gmail", "v1", credentials=creds)


def sheets_client():
    creds = get_credentials(["https://www.googleapis.com/auth/spreadsheets"])
    return build("sheets", "v4", credentials=creds).spreadsheets()


# ─── Telegram ─────────────────────────────────────────────────────────────────

def send_telegram(text):
    url     = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
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


# ─── Helpers ──────────────────────────────────────────────────────────────────

def normalise(s):
    """Lowercase + strip for loose name matching."""
    return s.strip().lower()


def get_header(headers, name):
    """Extract a header value from Gmail message headers list."""
    name_lower = name.lower()
    for h in headers:
        if h.get("name", "").lower() == name_lower:
            return h.get("value", "")
    return ""


def extract_sender_name(from_header):
    """
    Parse display name from a From header like:
      "James Chiu <james@cedar.com>"  →  "James Chiu"
      "james@cedar.com"               →  "james@cedar.com"
    """
    if "<" in from_header:
        return from_header.split("<")[0].strip().strip('"')
    return from_header.strip()


# ─── Core Logic ───────────────────────────────────────────────────────────────

def load_outreach_rows(svc_sheets):
    """Return list of (row_index_in_sheet, name, company, status)."""
    result = svc_sheets.values().get(
        spreadsheetId=SHEET_ID,
        range=SHEET_RANGE,
    ).execute()
    rows = result.get("values", [])
    active = []
    for i, row in enumerate(rows):
        # Pad short rows
        while len(row) <= COL_STATUS:
            row.append("")
        status = row[COL_STATUS].strip().lower()
        if status in ACTIVE_STATUSES:
            name    = row[COL_NAME].strip()    if len(row) > COL_NAME    else ""
            company = row[COL_COMPANY].strip() if len(row) > COL_COMPANY else ""
            if name:  # skip blank rows
                # Sheet row number = i+2 (1-indexed, row 1 is header)
                active.append((i + 2, name, company, status))
    return active


def search_gmail_unread(svc_gmail):
    """
    Search Gmail inbox for unread messages.
    Returns list of (message_id, sender_name, sender_email).
    """
    query    = "in:inbox is:unread"
    response = svc_gmail.users().messages().list(
        userId="me",
        q=query,
        maxResults=50,
    ).execute()

    messages = response.get("messages", [])
    results  = []
    for msg_stub in messages:
        msg = svc_gmail.users().messages().get(
            userId="me",
            id=msg_stub["id"],
            format="metadata",
            metadataHeaders=["From", "Subject"],
        ).execute()
        headers     = msg.get("payload", {}).get("headers", [])
        from_header = get_header(headers, "From")
        sender_name = extract_sender_name(from_header)
        # Extract email address
        if "<" in from_header and ">" in from_header:
            sender_email = from_header.split("<")[1].rstrip(">").strip()
        else:
            sender_email = from_header.strip()
        results.append((msg_stub["id"], sender_name, sender_email))
    return results


def names_match(sender_name, outreach_name):
    """
    Fuzzy-ish match: both lowercased, check if either is a substring of the other,
    or if first+last name words overlap with the sender display name.
    """
    s = normalise(sender_name)
    o = normalise(outreach_name)
    if s == o:
        return True
    # Check word overlap (both must share at least first name)
    s_parts = set(s.split())
    o_parts = set(o.split())
    overlap = s_parts & o_parts
    if overlap and len(overlap) >= min(1, len(o_parts)):
        return True
    return False


def update_status(svc_sheets, sheet_row, new_status="Replied"):
    """Update Status column (F) for a given sheet row number."""
    cell_range = f"Outreach!F{sheet_row}"
    svc_sheets.values().update(
        spreadsheetId=SHEET_ID,
        range=cell_range,
        valueInputOption="RAW",
        body={"values": [[new_status]]},
    ).execute()


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print(f"[{datetime.now(timezone.utc).isoformat()}] Gmail reply check starting...")

    try:
        svc_gmail  = gmail_client()
        svc_sheets = sheets_client()
    except Exception as e:
        print(f"ERROR: Auth failed — {e}", file=sys.stderr)
        sys.exit(1)

    # Load who we're waiting on
    outreach_rows = load_outreach_rows(svc_sheets)
    if not outreach_rows:
        print("No active outreach rows found. Nothing to check.")
        return

    print(f"Checking {len(outreach_rows)} active outreach contacts...")

    # Search Gmail
    try:
        unread_messages = search_gmail_unread(svc_gmail)
    except Exception as e:
        print(f"ERROR: Gmail search failed — {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(unread_messages)} unread messages in inbox.")

    # Match
    matched = []
    for msg_id, sender_name, sender_email in unread_messages:
        for sheet_row, outreach_name, company, status in outreach_rows:
            if names_match(sender_name, outreach_name):
                matched.append({
                    "msg_id": msg_id,
                    "sender_name": sender_name,
                    "sender_email": sender_email,
                    "sheet_row": sheet_row,
                    "outreach_name": outreach_name,
                    "company": company,
                })
                break  # one match per message is enough

    if not matched:
        print("No replies detected from outreach contacts.")
        return

    # Process matches
    notified = []
    for match in matched:
        try:
            update_status(svc_sheets, match["sheet_row"], "Replied")
            print(f"  ✓ Updated row {match['sheet_row']}: {match['outreach_name']} @ {match['company']} → Replied")
        except Exception as e:
            print(f"  ✗ Sheet update failed for {match['outreach_name']}: {e}", file=sys.stderr)
            continue

        try:
            msg = f"🟢 Reply from {match['outreach_name']} @ {match['company']} — check your inbox"
            send_telegram(msg)
            print(f"  ✓ Telegram sent: {msg}")
            notified.append(match)
        except Exception as e:
            print(f"  ✗ Telegram failed for {match['outreach_name']}: {e}", file=sys.stderr)

    print(f"\nDone. {len(notified)} replies detected and logged.")


if __name__ == "__main__":
    main()
