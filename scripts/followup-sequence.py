#!/usr/bin/env python3
"""
followup-sequence.py — Day 3/5/7/14 outreach follow-up reminder system

Runs daily at 14:30 UTC (9:30am EST) via cron.
Loads Outreach sheet, checks Days since sent, and sends Telegram reminders
for contacts that hit Day 3, 6, or 10 milestones.

Sheet columns (Outreach!A2:H100):
  A: Date (YYYY-MM-DD sent)
  B: Name
  C: Company
  D: Channel
  E: Type
  F: Status  (Sent / Replied / Meeting Booked / Stale)
  G: FollowUp (tracks stage: D3 / D6 / D10)
  H: Notes
"""

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone, date

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# ── Config ────────────────────────────────────────────────────────────────────
WORKSPACE        = "/root/.openclaw/workspace"
TELEGRAM_TOKEN   = "REDACTED"
TELEGRAM_CHAT_ID = "8768439197"
SHEET_ID         = "1o6XXLhpxFVZL5SlDKP8a56Y17brgmD7HWzAGe1Ei4Co"
SHEET_RANGE      = "Outreach!A2:H100"
TASKS_RANGE      = "Tasks!A2:F200"
GOG_TOKEN_FILE   = os.path.join(WORKSPACE, "config/gog-token.json")
CLIENT_SECRET    = os.path.join(WORKSPACE, "google_client_secret.json")

# Column indices (0-based) — Outreach sheet
COL_DATE     = 0  # A
COL_NAME     = 1  # B
COL_COMPANY  = 2  # C
COL_CHANNEL  = 3  # D
COL_TYPE     = 4  # E
COL_STATUS   = 5  # F
COL_FOLLOWUP = 6  # G
COL_NOTES    = 7  # H

# Column indices (0-based) — Tasks sheet
# Task ID | Name | Project ID | Status | Due Date | Notes
TASK_COL_ID        = 0
TASK_COL_NAME      = 1
TASK_COL_PROJECT   = 2
TASK_COL_STATUS    = 3
TASK_COL_DUE       = 4
TASK_COL_NOTES     = 5


# ── Google Sheets ─────────────────────────────────────────────────────────────

def sheets_client():
    try:
        with open(GOG_TOKEN_FILE) as f:
            tok = json.load(f)
        with open(CLIENT_SECRET) as f:
            secret = json.load(f)
        cfg = secret.get("installed") or secret.get("web") or secret
        creds = Credentials(
            token=None,
            refresh_token=tok["refresh_token"],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=cfg["client_id"],
            client_secret=cfg["client_secret"],
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        return build("sheets", "v4", credentials=creds).spreadsheets()
    except Exception as e:
        print(f"[ERROR] Sheets auth failed: {e}", file=sys.stderr)
        return None


def load_tasks_due_today(svc):
    """Load tasks from Tasks tab that are todo AND due today or overdue."""
    try:
        result = svc.values().get(
            spreadsheetId=SHEET_ID,
            range=TASKS_RANGE,
        ).execute()
        rows = result.get("values", [])
    except Exception as e:
        print(f"[ERROR] Could not load Tasks sheet: {e}", file=sys.stderr)
        return []

    today = datetime.now(timezone.utc).date()
    due = []
    for row in rows:
        while len(row) < 6:
            row.append("")
        task_id  = row[TASK_COL_ID].strip()
        name     = row[TASK_COL_NAME].strip()
        status   = row[TASK_COL_STATUS].strip().lower()
        due_str  = row[TASK_COL_DUE].strip()

        if status != "todo":
            continue
        if not due_str or due_str.upper() == "TBD":
            continue
        try:
            due_date = datetime.strptime(due_str, "%Y-%m-%d").date()
        except ValueError:
            continue
        if due_date <= today:
            due.append({"id": task_id, "name": name, "due": due_date, "overdue": due_date < today})

    return due


def load_outreach_rows(svc):
    """Load all outreach rows from sheet. Returns (rows, raw_values)."""
    try:
        result = svc.values().get(
            spreadsheetId=SHEET_ID,
            range=SHEET_RANGE,
        ).execute()
        return result.get("values", [])
    except Exception as e:
        print(f"[ERROR] Could not load Outreach sheet: {e}", file=sys.stderr)
        return []


def update_followup_cell(svc, row_index: int, value: str):
    """Update the FollowUp column (G) for a given row index (0-based from A2)."""
    row_num = row_index + 2  # +2 because sheet is 1-indexed and we skip header (row 1)
    cell_range = f"Outreach!G{row_num}"
    try:
        svc.values().update(
            spreadsheetId=SHEET_ID,
            range=cell_range,
            valueInputOption="RAW",
            body={"values": [[value]]},
        ).execute()
        print(f"  ✅ Updated G{row_num} → {value}")
    except Exception as e:
        print(f"  ⚠ Could not update G{row_num}: {e}", file=sys.stderr)


def update_status_cell(svc, row_index: int, value: str):
    """Update the Status column (F) for a given row index."""
    row_num = row_index + 2
    cell_range = f"Outreach!F{row_num}"
    try:
        svc.values().update(
            spreadsheetId=SHEET_ID,
            range=cell_range,
            valueInputOption="RAW",
            body={"values": [[value]]},
        ).execute()
        print(f"  ✅ Updated F{row_num} → {value}")
    except Exception as e:
        print(f"  ⚠ Could not update F{row_num}: {e}", file=sys.stderr)


# ── Telegram ──────────────────────────────────────────────────────────────────

def send_telegram(text: str):
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


# ── Follow-up message drafts ──────────────────────────────────────────────────

def draft_day3(name: str, company: str, channel: str) -> str:
    """Day 3: simple check-in, re-state interest."""
    return (
        f"Hey {name.split()[0]},\n\n"
        f"Just circling back on {company}. Still very interested — happy to share more context if useful.\n\n"
        f"Hirsch"
    )


def draft_day5(name: str, company: str, channel: str) -> str:
    """Day 5: new angle."""
    return (
        f"Hey {name.split()[0]},\n\n"
        f"Following up on {company}. Happy to share a quick take on what I'd prioritize in the first 90 days if that's helpful.\n\n"
        f"Hirsch"
    )


def draft_day7(name: str, company: str, channel: str) -> str:
    """Day 7: check if timing is off."""
    return (
        f"Hey {name.split()[0]},\n\n"
        f"One more note on {company} — if the timing isn't right or the role is already filled, totally fine. Just want to make sure my note didn't get buried.\n\n"
        f"Hirsch"
    )


def draft_day14(name: str, company: str, channel: str) -> str:
    """Day 14: closing the loop."""
    return (
        f"Hey {name.split()[0]},\n\n"
        f"Closing the loop on {company}. No worries if it's not a fit — happy to stay in touch for the future.\n\n"
        f"Hirsch"
    )


STAGE_DRAFTERS = {
    "D3":  (3,  draft_day3),
    "D5":  (5,  draft_day5),
    "D7":  (7,  draft_day7),
    "D14": (14, draft_day14),
}

STAGE_ORDER = ["D3", "D5", "D7", "D14"]
STAGE_DAYS  = {"D3": 3, "D5": 5, "D7": 7, "D14": 14}


def next_stage(current_followup: str) -> str | None:
    """Return the next follow-up stage label, or None if done."""
    current = (current_followup or "").strip().upper()
    if not current:
        return "D3"
    if current == "D3":
        return "D6"
    if current == "D6":
        return "D10"
    return None  # D10 or beyond — done


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"[{datetime.now().isoformat()}] followup-sequence starting")

    svc = sheets_client()
    if not svc:
        print("[FATAL] Cannot connect to Google Sheets. Exiting.", file=sys.stderr)
        sys.exit(1)

    rows = load_outreach_rows(svc)
    print(f"  {len(rows)} rows loaded from Outreach sheet")

    today = datetime.now(timezone.utc).date()
    reminders = []

    for i, row in enumerate(rows):
        # Pad row to ensure all columns exist
        while len(row) < 8:
            row.append("")

        date_str  = row[COL_DATE].strip()
        name      = row[COL_NAME].strip()
        company   = row[COL_COMPANY].strip()
        channel   = row[COL_CHANNEL].strip()
        status    = row[COL_STATUS].strip()
        followup  = row[COL_FOLLOWUP].strip()

        # Skip if resolved
        if status in ("Replied", "Meeting Booked", "Stale"):
            continue

        # Skip if not sent
        if status != "Sent":
            continue

        # Parse sent date
        try:
            sent_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            print(f"  ⚠ Row {i+2}: bad date '{date_str}' — skipping")
            continue

        days_elapsed = (today - sent_date).days

        # Mark Stale at day 15+
        if days_elapsed >= 15:
            current_stage = followup.upper()
            if current_stage != "STALE":
                print(f"  🪦 {name} @ {company}: {days_elapsed}d elapsed → marking Stale")
                update_status_cell(svc, i, "Stale")
            continue

        # Determine which stage should fire today
        stage_to_fire = None
        for stage in STAGE_ORDER:
            required_days = STAGE_DAYS[stage]
            already_done = followup.upper() in [s for s in STAGE_ORDER if STAGE_DAYS[s] <= required_days]
            already_done = (followup.upper() >= stage) if followup.upper() in STAGE_ORDER else False

            if days_elapsed >= required_days and followup.upper() < stage:
                stage_to_fire = stage
                break

        # Simpler logic: find the highest stage we've passed but not yet marked
        stage_to_fire = None
        for stage in reversed(STAGE_ORDER):
            if days_elapsed >= STAGE_DAYS[stage]:
                # This stage is due or overdue
                current = followup.strip().upper()
                # Check if we already fired this stage or later
                if current not in STAGE_ORDER:
                    # Never fired any stage yet — fire the earliest due
                    stage_to_fire = None
                    for s in STAGE_ORDER:
                        if days_elapsed >= STAGE_DAYS[s] and current not in [x for x in STAGE_ORDER if STAGE_DAYS[x] <= STAGE_DAYS[s]]:
                            stage_to_fire = s
                            break
                    break
                else:
                    current_idx = STAGE_ORDER.index(current)
                    stage_idx   = STAGE_ORDER.index(stage)
                    if stage_idx > current_idx:
                        stage_to_fire = stage
                    break

        if not stage_to_fire:
            continue

        # Build the draft and reminder
        _, drafter = STAGE_DRAFTERS[stage_to_fire]
        draft = drafter(name, company, channel)

        reminder_lines = [
            f"🔔 *Follow-up {stage_to_fire}: {name} @ {company}*",
            f"_{days_elapsed} days since sent — {channel}_",
            "",
            "Draft:",
            f"```\n{draft}\n```",
        ]
        reminder_text = "\n".join(reminder_lines)
        reminders.append((i, stage_to_fire, name, company, reminder_text))

    print(f"\n  {len(reminders)} follow-up reminder(s) to send")

    for i, stage, name, company, reminder_text in reminders:
        print(f"  → Sending {stage} reminder for {name} @ {company}")
        try:
            send_telegram(reminder_text)
            update_followup_cell(svc, i, stage)
            print(f"     ✅ Sent + sheet updated")
        except Exception as e:
            print(f"     ⚠ Telegram failed: {e}", file=sys.stderr)

    if not reminders:
        print("  ✅ No follow-ups due today.")

    # ── Tasks due today / overdue ─────────────────────────────────────────────
    tasks_due = load_tasks_due_today(svc)
    print(f"\n  {len(tasks_due)} task(s) due today or overdue")

    if tasks_due:
        lines = ["📋 *Tasks due today:*", ""]
        for t in tasks_due:
            label = "⚠️ overdue" if t["overdue"] else "today"
            lines.append(f"• [{t['id']}] {t['name']} — {label} ({t['due'].strftime('%b %d')})")
        task_msg = "\n".join(lines)
        print(f"  → Sending tasks reminder")
        try:
            send_telegram(task_msg)
        except Exception as e:
            print(f"  ⚠ Tasks Telegram failed: {e}", file=sys.stderr)

    print(f"[{datetime.now().isoformat()}] followup-sequence done\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
