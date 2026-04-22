#!/usr/bin/env python3
# followup-sequence.py -- Morning Brief (redesigned 2026-04-10)
#
# Sections:
#   1. Follow-ups due      Outreach rows past D3/D7/D14 threshold
#   2. First contacts      Jobs with Network Path not yet in Outreach (carry-forward)
#   3. New contacts today  Up to 5 Jobs by Priority Score, not yet actioned
#   4. Tasks               Due today or overdue, not done
#
# Always sends unless all four sections are empty.
# Follow-up cadence: D3=3d  D7=7d  D14=14d (from Outreach col-A date)
# Stage normalized on read: "D14 (Apr 15)" -> "D14"
# On fire: col-A=today, col-G=next stage or "Done"

import json, os, re, sys, urllib.request
from datetime import datetime, timezone
from google.oauth2 import service_account
from googleapiclient.discovery import build
sys.path.insert(0, os.path.dirname(__file__))
from state import fired_today, mark_fired

WORKSPACE        = "/root/.openclaw/workspace"
TELEGRAM_TOKEN   = "REDACTED"
TELEGRAM_CHAT_ID = "8768439197"
SHEET_ID         = "1o6XXLhpxFVZL5SlDKP8a56Y17brgmD7HWzAGe1Ei4Co"
SA_KEY_FILE      = os.path.join(WORKSPACE, "config/sterl-sheets-key.json")
SHEETS_SCOPES    = ["https://www.googleapis.com/auth/spreadsheets"]

MAX_NEW_CONTACTS = 5
STAGE_ORDER = ["D3", "D7", "D14"]
STAGE_DAYS  = {"D3": 3, "D7": 7, "D14": 14}
TERMINAL_STATUS       = {"replied", "meeting booked", "stale"}
SKIP_JOB_STATUSES     = {"removed", "paused"}
ACTIONED_JOB_STATUSES = {
    "applied", "screening", "interviewing", "paused",
    "rejected", "passed", "hired", "declined",
    # "outreaching" is intentionally NOT here — stays visible until confirmed referral
}


def sheets_client():
    try:
        creds = service_account.Credentials.from_service_account_file(
            SA_KEY_FILE, scopes=SHEETS_SCOPES
        )
        return build("sheets", "v4", credentials=creds).spreadsheets()
    except Exception as e:
        print("[ERROR] Sheets auth: " + str(e), file=sys.stderr)
        return None


def get_range(svc, r):
    try:
        return svc.values().get(spreadsheetId=SHEET_ID, range=r).execute().get("values", [])
    except Exception as e:
        print("[ERROR] get_range " + r + ": " + str(e), file=sys.stderr)
        return []


def pad(row, n):
    while len(row) < n:
        row.append("")
    return row


def normalize_stage(raw):
    if not raw:
        return ""
    m = re.match(r"(D\d+)", raw.strip(), re.IGNORECASE)
    if m:
        return m.group(1).upper()
    return raw.strip().title()


def next_stage(current):
    if current not in STAGE_ORDER:
        return "Done"
    idx = STAGE_ORDER.index(current)
    return STAGE_ORDER[idx + 1] if idx + 1 < len(STAGE_ORDER) else "Done"


def update_outreach_row(svc, sheet_row, date_str, stage):
    body = {
        "valueInputOption": "USER_ENTERED",
        "data": [
            {"range": "Outreach!A" + str(sheet_row), "values": [[date_str]]},
            {"range": "Outreach!G" + str(sheet_row), "values": [[stage]]},
        ],
    }
    try:
        svc.values().batchUpdate(spreadsheetId=SHEET_ID, body=body).execute()
    except Exception as e:
        print("[ERROR] update row " + str(sheet_row) + ": " + str(e), file=sys.stderr)


def md_to_html(text):
    """Convert simple *bold* markdown to HTML bold tags for Telegram."""
    import re
    # Replace *bold* with <b>bold</b>
    text = re.sub(r'\*(.+?)\*', r'<b>\1</b>', text)
    return text

def send_telegram(text):
    url = "https://api.telegram.org/bot" + TELEGRAM_TOKEN + "/sendMessage"
    payload = json.dumps(
        {"chat_id": TELEGRAM_CHAT_ID, "text": md_to_html(text), "parse_mode": "HTML"}
    ).encode()
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        print("[ERROR] Telegram: " + str(e), file=sys.stderr)
        return False


# ---------------------------------------------------------------------------
# Section 1 -- Follow-ups due
# ---------------------------------------------------------------------------

def section_followups(svc, today, today_str):
    # Columns: A=Date, B=Name, C=Company, D=Channel, E=Message Type, F=Status, G=Follow-Up Date, H=Notes
    rows = get_range(svc, "Outreach!A2:H200")
    due = []
    for i, row in enumerate(rows):
        row = pad(row, 8)
        name       = row[1].strip()
        company    = row[2].strip()
        channel    = row[3].strip()
        status     = row[5].strip().lower()
        fu_str     = row[6].strip()

        if not name:
            continue
        if status in TERMINAL_STATUS:
            continue
        if not fu_str:
            continue

        try:
            fu_date = datetime.strptime(fu_str, "%Y-%m-%d").date()
        except ValueError:
            continue

        if today >= fu_date:
            label = name + " @ " + company if company else name
            due.append({"label": label, "channel": channel})

    return due


# ---------------------------------------------------------------------------
# Section 2 -- First contacts not yet sent (carry-forward)
# ---------------------------------------------------------------------------

def section_first_contacts(svc, outreach_names):
    rows = get_range(svc, "Jobs!A2:J200")
    pending = []
    for row in rows:
        row = pad(row, 10)
        company      = row[0].strip()
        role         = row[1].strip()
        network_path = row[7].strip()
        status       = row[8].strip().lower()

        if status in SKIP_JOB_STATUSES:
            continue
        if not network_path:
            continue

        # Extract contact name from "Name (Title at Company)" format
        contact_name = network_path.split("(")[0].strip()

        # Skip if already in Outreach
        if contact_name.lower() in outreach_names:
            continue

        pending.append({
            "contact": contact_name,
            "company": company,
            "role": role,
            "network_path": network_path,
        })

    return pending[:MAX_NEW_CONTACTS]


# ---------------------------------------------------------------------------
# Section 3 -- New contacts today (up to 5, by priority score)
# ---------------------------------------------------------------------------

def section_new_contacts(svc, outreach_names):
    rows = get_range(svc, "Jobs!A2:J200")
    candidates = []
    for row in rows:
        row = pad(row, 10)
        company      = row[0].strip()
        role         = row[1].strip()
        network_path = row[7].strip()
        status       = row[8].strip().lower()

        if status in SKIP_JOB_STATUSES:
            continue
        if status in ACTIONED_JOB_STATUSES:
            continue
        if not network_path:
            continue

        contact_name = network_path.split("(")[0].strip()
        if contact_name.lower() in outreach_names:
            continue

        try:
            priority = float(row[4])
        except (ValueError, IndexError):
            priority = 0.0

        candidates.append({
            "contact": contact_name,
            "company": company,
            "role": role,
            "priority": priority,
        })

    candidates.sort(key=lambda x: x["priority"], reverse=True)
    return candidates[:MAX_NEW_CONTACTS]


# ---------------------------------------------------------------------------
# Section 4 -- Tasks due today or overdue
# ---------------------------------------------------------------------------

def section_tasks(svc, today):
    rows = get_range(svc, "Tasks!A2:F200")
    due = []
    undated = []
    for row in rows:
        row = pad(row, 6)
        status      = row[3].strip().lower()
        due_str_val = row[4].strip()
        name        = row[1].strip()
        notes       = row[5].strip()

        if not name:
            continue
        if status in {"done", "cancelled", "complete"}:
            continue

        if not due_str_val:
            undated.append({"label": name, "due": None})
            continue

        try:
            due_date = datetime.strptime(due_str_val, "%Y-%m-%d").date()
        except ValueError:
            continue
        if due_date <= today:
            label = name
            if notes:
                label += " -- " + notes[:60]
            due.append({"label": label, "due": due_str_val})
    return due, undated


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if fired_today("morning_brief"):
        print("[INFO] Morning brief already sent today. Skipping.")
        return

    today     = datetime.now(timezone.utc).date()
    today_str = today.strftime("%Y-%m-%d")

    svc = sheets_client()
    if svc is None:
        print("[ERROR] Could not create Sheets client. Exiting.", file=sys.stderr)
        sys.exit(1)

    # Build set of already-outreached names for dedup
    outreach_rows  = get_range(svc, "Outreach!B2:B200")
    outreach_names = {pad(r, 1)[0].strip().lower() for r in outreach_rows if r}

    # Collect sections
    followups    = section_followups(svc, today, today_str)
    new_contacts = section_new_contacts(svc, outreach_names)
    tasks, undated_tasks = section_tasks(svc, today)

    # Bail if truly nothing
    if not followups and not new_contacts and not tasks and not undated_tasks:
        print("[INFO] Nothing to report today.")
        return

    lines = ["<b>Morning Brief — " + today_str + "</b>", ""]

    # Section 1 — Follow-ups (highest priority)
    if followups:
        lines.append("<b>1. Follow-ups due (" + str(len(followups)) + ")</b>")
        for item in followups:
            suffix = " via " + item["channel"] if item["channel"] else ""
            lines.append("  • " + item["label"] + suffix)
        lines.append("")

    # Section 2 — New contacts (top 5, carry-forward included)
    if new_contacts:
        lines.append("<b>2. New contacts for today (" + str(len(new_contacts)) + ")</b>")
        for item in new_contacts:
            lines.append("  • " + item["contact"] + " @ " + item["company"] + " — " + item["role"])
        lines.append("")

    # Section 3 — Tasks due/overdue
    if tasks:
        lines.append("<b>3. Tasks due / overdue (" + str(len(tasks)) + ")</b>")
        for item in tasks:
            lines.append("  • " + item["label"] + " (due " + item["due"] + ")")
        lines.append("")

    # Section 4 — Undated tasks
    if undated_tasks:
        lines.append("<b>4. No due date set (" + str(len(undated_tasks)) + ")</b>")
        for item in undated_tasks:
            lines.append("  • " + item["label"])

    message = "\n".join(lines)
    print(message)
    send_telegram(message)
    mark_fired("morning_brief")


if __name__ == "__main__":
    main()
