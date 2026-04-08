#!/usr/bin/env python3
"""
friday-checkin.py — Domain 3: Ideas OS
Runs every Friday at 5:45pm EST (22:45 UTC) via cron.
Pulls data from Google Sheets and sends a weekly check-in to Telegram.
"""

import os
import json
import datetime
import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

WORKSPACE = "/root/.openclaw/workspace"
SHEET_ID = "1o6XXLhpxFVZL5SlDKP8a56Y17brgmD7HWzAGe1Ei4Co"
LOG_FILE = os.path.join(WORKSPACE, "logs/friday-checkin.log")
TELEGRAM_BOT = "REDACTED"
TELEGRAM_CHAT = "8768439197"

# Tab names (adjust if actual sheet tab names differ)
TAB_JOBS = "Jobs"
TAB_OUTREACH = "Outreach"
TAB_INTERVIEWS = "Interviews"
TAB_IDEAS = "Ideas"


def log(msg):
    print(msg)
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(msg + "\n")


def get_creds():
    with open(os.path.join(WORKSPACE, "config/gog-token.json")) as f:
        tok = json.load(f)
    with open(os.path.join(WORKSPACE, "google_client_secret.json")) as f:
        secret = json.load(f)
    cfg = secret.get("installed") or secret.get("web") or secret
    creds = Credentials(
        token=tok.get("token"),
        refresh_token=tok["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=cfg["client_id"],
        client_secret=cfg["client_secret"],
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
        ],
    )
    if creds.expired or not creds.valid:
        creds.refresh(Request())
    return creds


def get_sheet_values(service, tab, range_suffix=""):
    """Fetch all values from a tab. Returns list of rows (each row is a list)."""
    try:
        range_name = f"{tab}!A:Z" if not range_suffix else f"{tab}!{range_suffix}"
        result = service.spreadsheets().values().get(
            spreadsheetId=SHEET_ID, range=range_name
        ).execute()
        return result.get("values", [])
    except Exception as e:
        log(f"[friday-checkin] Could not fetch tab '{tab}': {e}")
        return []


def get_week_bounds():
    """Return (start_of_week, end_of_next_week) as date objects."""
    today = datetime.date.today()
    # Week starts Monday
    start_of_week = today - datetime.timedelta(days=today.weekday())
    end_of_week = start_of_week + datetime.timedelta(days=6)
    end_of_next_week = end_of_week + datetime.timedelta(days=7)
    return start_of_week, end_of_week, end_of_next_week


def parse_date(s):
    """Try to parse a date string. Returns datetime.date or None."""
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d %H:%M UTC", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    return None


def rows_to_dicts(rows):
    """Convert sheet rows (with header row) to list of dicts."""
    if not rows:
        return []
    headers = [h.strip().lower() for h in rows[0]]
    result = []
    for row in rows[1:]:
        # Pad row to header length
        padded = row + [""] * (len(headers) - len(row))
        result.append(dict(zip(headers, padded)))
    return result


def count_outreach_this_week(service, start_of_week, end_of_week):
    """Count outreach messages sent this week."""
    rows = get_sheet_values(service, TAB_OUTREACH)
    if not rows:
        return 0
    records = rows_to_dicts(rows)
    count = 0
    sent_statuses = {"sent", "replied", "meeting booked"}
    for r in records:
        status = r.get("status", "").strip().lower()
        if status not in sent_statuses:
            continue
        # Check date field (try "date sent", "date", "sent date")
        date_val = r.get("date sent") or r.get("date") or r.get("sent date") or r.get("last update") or ""
        d = parse_date(date_val)
        if d and start_of_week <= d <= end_of_week:
            count += 1
    return count


def count_jobs_actioned_this_week(service, start_of_week, end_of_week):
    """Count jobs where status was changed from 'new' this week (using Last Update date)."""
    rows = get_sheet_values(service, TAB_JOBS)
    if not rows:
        return 0
    records = rows_to_dicts(rows)
    count = 0
    for r in records:
        status = r.get("status", "").strip().lower()
        if status == "new":
            continue  # still new, hasn't been actioned
        date_val = r.get("last update") or r.get("date updated") or r.get("date") or ""
        d = parse_date(date_val)
        if d and start_of_week <= d <= end_of_week:
            count += 1
    return count


def get_interviews(service, start_of_week, end_of_next_week):
    """Get interviews scheduled this week or next week."""
    rows = get_sheet_values(service, TAB_INTERVIEWS)
    if not rows:
        return []
    records = rows_to_dicts(rows)
    interviews = []
    for r in records:
        date_val = r.get("date") or r.get("interview date") or r.get("scheduled date") or ""
        d = parse_date(date_val)
        if d and start_of_week <= d <= end_of_next_week:
            company = r.get("company") or r.get("name") or "Unknown"
            stage = r.get("stage") or r.get("status") or r.get("round") or ""
            interviews.append({"company": company, "date": d, "stage": stage})
    return interviews


def get_active_ideas(service):
    """Get ideas with status = Activated."""
    rows = get_sheet_values(service, TAB_IDEAS)
    if not rows:
        return []
    records = rows_to_dicts(rows)
    active = []
    for r in records:
        status = r.get("status", "").strip().lower()
        if status == "activated":
            idea = r.get("idea") or r.get("name") or "Unnamed idea"
            first_step = r.get("first step") or ""
            active.append({"idea": idea, "first_step": first_step})
    return active


def get_parked_ideas(service):
    """Get parked ideas that are older than 2 weeks."""
    rows = get_sheet_values(service, TAB_IDEAS)
    if not rows:
        return []
    records = rows_to_dicts(rows)
    today = datetime.date.today()
    parked = []
    for r in records:
        status = r.get("status", "").strip().lower()
        if status != "parked":
            continue
        idea = r.get("idea") or r.get("name") or "Unnamed idea"
        date_val = r.get("last update") or r.get("due date") or ""
        d = parse_date(date_val)
        weeks_ago = None
        if d:
            delta = today - d
            weeks_ago = delta.days // 7
            if weeks_ago >= 2:
                parked.append({"idea": idea, "weeks_ago": weeks_ago})
        else:
            # No date — include with unknown age
            parked.append({"idea": idea, "weeks_ago": None})
    return parked


def build_checkin_message(outreach_count, jobs_count, interviews, active_ideas, parked_ideas):
    lines = ["📊 *Weekly check-in*", ""]

    # This week stats
    lines.append("*This week:*")
    lines.append(f"• {outreach_count} outreach sent")
    lines.append(f"• {jobs_count} jobs actioned")

    if interviews:
        this_week_iv = [i for i in interviews if i["date"] <= datetime.date.today() + datetime.timedelta(days=6)]
        lines.append(f"• {len(interviews)} interview(s) scheduled/upcoming")
    else:
        lines.append("• 0 interviews")

    lines.append("")

    # Interviews detail
    if interviews:
        lines.append("*Interviews:*")
        for iv in interviews[:5]:
            stage = f" — {iv['stage']}" if iv["stage"] else ""
            lines.append(f"• {iv['company']} on {iv['date'].strftime('%b %d')}{stage}")
        lines.append("")

    # Active projects
    if active_ideas:
        lines.append("*Active projects:*")
        for a in active_ideas[:5]:
            step = f" — {a['first_step']}" if a["first_step"] else ""
            # Truncate long idea names
            name = a["idea"][:50] + ("..." if len(a["idea"]) > 50 else "")
            lines.append(f"• {name}{step}")
        lines.append("")

    # Parked review
    if parked_ideas:
        lines.append("*Parked (review):*")
        for p in parked_ideas[:5]:
            name = p["idea"][:50] + ("..." if len(p["idea"]) > 50 else "")
            if p["weeks_ago"] is not None:
                lines.append(f"• {name} — parked {p['weeks_ago']} week(s) ago. Still relevant?")
            else:
                lines.append(f"• {name} — parked (date unknown). Still relevant?")
        lines.append("")

    lines.append("*Is the pipeline moving? Yes or no.*")

    # Cap at 20 lines
    if len(lines) > 20:
        lines = lines[:19] + ["*Is the pipeline moving? Yes or no.*"]

    return "\n".join(lines)


def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT}/sendMessage"
    resp = requests.post(
        url,
        json={"chat_id": TELEGRAM_CHAT, "text": text, "parse_mode": "Markdown"},
        timeout=10,
    )
    if resp.status_code != 200:
        log(f"[friday-checkin] Telegram error: {resp.text}")
    else:
        log(f"[friday-checkin] Weekly check-in sent.")


def main():
    now_str = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    log(f"\n[{now_str}] [friday-checkin] Starting weekly check-in...")

    start_of_week, end_of_week, end_of_next_week = get_week_bounds()
    log(f"[friday-checkin] Week: {start_of_week} to {end_of_week}")

    creds = get_creds()
    service = build("sheets", "v4", credentials=creds)

    outreach_count = count_outreach_this_week(service, start_of_week, end_of_week)
    jobs_count = count_jobs_actioned_this_week(service, start_of_week, end_of_week)
    interviews = get_interviews(service, start_of_week, end_of_next_week)
    active_ideas = get_active_ideas(service)
    parked_ideas = get_parked_ideas(service)

    log(f"[friday-checkin] outreach={outreach_count}, jobs={jobs_count}, "
        f"interviews={len(interviews)}, active={len(active_ideas)}, parked={len(parked_ideas)}")

    msg = build_checkin_message(outreach_count, jobs_count, interviews, active_ideas, parked_ideas)
    log(f"[friday-checkin] Message:\n{msg}")

    send_telegram(msg)
    log(f"[friday-checkin] Done.")


if __name__ == "__main__":
    main()
