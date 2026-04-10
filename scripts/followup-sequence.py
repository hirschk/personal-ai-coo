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
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

WORKSPACE        = "/root/.openclaw/workspace"
TELEGRAM_TOKEN   = "REDACTED"
TELEGRAM_CHAT_ID = "8768439197"
SHEET_ID         = "1o6XXLhpxFVZL5SlDKP8a56Y17brgmD7HWzAGe1Ei4Co"
GOG_TOKEN_FILE   = os.path.join(WORKSPACE, "config/gog-token.json")
CLIENT_SECRET    = os.path.join(WORKSPACE, "google_client_secret.json")

MAX_NEW_CONTACTS = 5
STAGE_ORDER = ["D3", "D7", "D14"]
STAGE_DAYS  = {"D3": 3, "D7": 7, "D14": 14}
TERMINAL_STATUS       = {"replied", "meeting booked", "stale"}
SKIP_JOB_STATUSES     = {"removed"}
ACTIONED_JOB_STATUSES = {
    "applied", "screening", "interviewing", "paused",
    "rejected", "passed", "hired", "declined",
}


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


def send_telegram(text):
    url = "https://api.telegram.org/bot" + TELEGRAM_TOKEN + "/sendMessage"
    payload = json.dumps(
        {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
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
    rows = get_range(svc, "Outreach!A2:H200")
    due = []
    for i, row in enumerate(rows):
        row = pad(row, 8)
        status  = row[5].strip().lower()
        raw_stg = row[6].strip()
        d_str   = row[0].strip()
        name    = row[1].strip()
        company = row[2].strip()
        channel = row[3].strip()

        if status in TERMINAL_STATUS:
            continue

        stage = normalize_stage(raw_stg)
        if stage.lower() in {"done", ""} or stage not in STAGE_ORDER:
            continue

        if not d_str:
            continue

        try:
            last_touch = datetime.strptime(d_str, "%Y-%m-%d").date()
        except ValueError:
            continue

        days_since = (today - last_touch).days
        required   = STAGE_DAYS[stage]

        if days_since >= required:
            label = name + " @ " + company if company else name
            due.append({"label": label, "stage": stage, "channel": channel})
            # advance stage; sheet row = i+2 (header is row 1, data starts row 2)
            update_outreach_row(svc, i + 2, today_str, next_stage(stage))

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

    return pending


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
    for row in rows:
        row = pad(row, 6)
        status      = row[3].strip().lower()
        due_str_val = row[4].strip()
        name        = row[1].strip()
        notes       = row[5].strip()

        if status in {"done", "cancelled", "complete"}:
            continue
        if not due_str_val:
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
    return due


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
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
    followups      = section_followups(svc, today, today_str)
    first_contacts = section_first_contacts(svc, outreach_names)
    new_contacts   = section_new_contacts(svc, outreach_names)
    tasks          = section_tasks(svc, today)

    # Bail if truly nothing
    if not followups and not first_contacts and not new_contacts and not tasks:
        print("[INFO] Nothing to report today.")
        return

    lines = ["*Morning Brief* -- " + today_str, ""]

    # Section 1
    if followups:
        lines.append("*1. Follow-ups due (" + str(len(followups)) + ")*")
        for item in followups:
            lines.append("  * [" + item["stage"] + "] " + item["label"] + " via " + item["channel"])
        lines.append("")

    # Section 2
    if first_contacts:
        lines.append("*2. First contacts not yet sent (" + str(len(first_contacts)) + ")*")
        for item in first_contacts:
            lines.append("  * " + item["contact"] + " @ " + item["company"] + " -- " + item["role"])
        lines.append("")

    # Section 3
    if new_contacts:
        lines.append("*3. New contacts for today (" + str(len(new_contacts)) + ")*")
        for item in new_contacts:
            lines.append("  * " + item["contact"] + " @ " + item["company"] + " -- " + item["role"])
        lines.append("")

    # Section 4
    if tasks:
        lines.append("*4. Tasks due / overdue (" + str(len(tasks)) + ")*")
        for item in tasks:
            lines.append("  * " + item["label"] + " (due " + item["due"] + ")")

    message = "\n".join(lines)
    print(message)
    send_telegram(message)


if __name__ == "__main__":
    main()
