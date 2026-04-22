#!/usr/bin/env python3
"""
friday-checkin.py -- Weekly check-in
Runs every Friday at 5:45pm EST (22:45 UTC) via cron.
Pulls data from Google Sheets and sends a weekly check-in to Telegram.
Includes: outreach/jobs/interviews summary, active projects with task counts,
overdue free-floating tasks.
"""

import os
import json
import datetime
import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build

WORKSPACE = "/root/.openclaw/workspace"
SHEET_ID = "1o6XXLhpxFVZL5SlDKP8a56Y17brgmD7HWzAGe1Ei4Co"
LOG_FILE = os.path.join(WORKSPACE, "logs/friday-checkin.log")
TELEGRAM_BOT = "REDACTED"
TELEGRAM_CHAT = "8768439197"

TAB_JOBS = "Jobs"
TAB_OUTREACH = "Outreach"
TAB_INTERVIEWS = "Interviews"
TAB_PROJECTS = "Projects"
TAB_TASKS = "Tasks"


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


def get_sheet_values(service, tab, range_suffix=""):
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
    today = datetime.date.today()
    start_of_week = today - datetime.timedelta(days=today.weekday())
    end_of_week = start_of_week + datetime.timedelta(days=6)
    end_of_next_week = end_of_week + datetime.timedelta(days=7)
    return start_of_week, end_of_week, end_of_next_week


def parse_date(s):
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    return None


def rows_to_dicts(rows):
    if not rows:
        return []
    headers = [h.strip().lower() for h in rows[0]]
    result = []
    for row in rows[1:]:
        padded = row + [""] * (len(headers) - len(row))
        result.append(dict(zip(headers, padded)))
    return result

def count_outreach_this_week(service, start_of_week, end_of_week):
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
        date_val = (r.get("date sent") or r.get("date") or r.get("sent date") or r.get("last update") or "")
        d = parse_date(date_val)
        if d and start_of_week <= d <= end_of_week:
            count += 1
    return count


def count_jobs_actioned_this_week(service, start_of_week, end_of_week):
    rows = get_sheet_values(service, TAB_JOBS)
    if not rows:
        return 0
    records = rows_to_dicts(rows)
    count = 0
    for r in records:
        status = r.get("status", "").strip().lower()
        if status == "new":
            continue
        date_val = (r.get("last update") or r.get("date updated") or r.get("date") or "")
        d = parse_date(date_val)
        if d and start_of_week <= d <= end_of_week:
            count += 1
    return count


def get_interviews(service, start_of_week, end_of_next_week):
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


def get_active_projects(service):
    """Get active projects with their incomplete task count."""
    proj_rows = get_sheet_values(service, TAB_PROJECTS)
    task_rows = get_sheet_values(service, TAB_TASKS)
    if not proj_rows:
        return []
    projects = rows_to_dicts(proj_rows)
    tasks = rows_to_dicts(task_rows) if task_rows else []
    incomplete_by_project = {}
    for t in tasks:
        pid = (t.get("project id") or "").strip()
        status = (t.get("status") or "").strip().lower()
        if pid and status not in ("done", "parked"):
            incomplete_by_project[pid] = incomplete_by_project.get(pid, 0) + 1
    active = []
    for p in projects:
        status = (p.get("status") or "").strip().lower()
        if status != "active":
            continue
        pid = (p.get("project id") or "").strip()
        name = (p.get("name") or "Unnamed project")[:60]
        incomplete = incomplete_by_project.get(pid, 0)
        active.append({"id": pid, "name": name, "incomplete_tasks": incomplete})
    return active


def get_overdue_solo_tasks(service):
    """Get overdue free-floating tasks (no Project ID, status=todo, due date past)."""
    rows = get_sheet_values(service, TAB_TASKS)
    if not rows:
        return []
    records = rows_to_dicts(rows)
    today = datetime.date.today()
    overdue = []
    for r in records:
        pid = (r.get("project id") or "").strip()
        if pid:
            continue
        status = (r.get("status") or "").strip().lower()
        if status != "todo":
            continue
        due_str = (r.get("due date") or "").strip()
        if not due_str or due_str.upper() == "TBD":
            continue
        d = parse_date(due_str)
        if d and d < today:
            task_id = (r.get("task id") or "").strip()
            name = (r.get("name") or "Unnamed task")[:60]
            overdue.append({"id": task_id, "name": name, "due": d})
    return overdue


def build_checkin_message(outreach_count, jobs_count, interviews, active_projects, overdue_tasks):
    lines = ["📊 *Weekly check-in*", ""]
    lines.append("*This week:*")
    lines.append(f"• {outreach_count} outreach sent")
    lines.append(f"• {jobs_count} jobs actioned")
    if interviews:
        lines.append(f"• {len(interviews)} interview(s) scheduled/upcoming")
    else:
        lines.append("• 0 interviews")
    lines.append("")
    if interviews:
        lines.append("*Interviews:*")
        for iv in interviews[:5]:
            stage = f" — {iv['stage']}" if iv["stage"] else ""
            lines.append(f"• {iv['company']} on {iv['date'].strftime('%b %d')}{stage}")
        lines.append("")
    if active_projects:
        lines.append("*Active projects:*")
        for p in active_projects[:8]:
            task_note = f" — {p['incomplete_tasks']} open task(s)" if p["incomplete_tasks"] else " — no linked tasks"
            name = p["name"][:55] + ("..." if len(p["name"]) > 55 else "")
            lines.append(f"• [{p['id']}] {name}{task_note}")
        lines.append("")
    if overdue_tasks:
        lines.append("*Overdue tasks:*")
        for t in overdue_tasks[:6]:
            lines.append(f"• [{t['id']}] {t['name']} — due {t['due'].strftime('%b %d')}")
        lines.append("")
    lines.append("*Is the pipeline moving? Yes or no.*")
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
    active_projects = get_active_projects(service)
    overdue_tasks = get_overdue_solo_tasks(service)
    log(f"[friday-checkin] outreach={outreach_count}, jobs={jobs_count}, "
        f"interviews={len(interviews)}, active_projects={len(active_projects)}, overdue_tasks={len(overdue_tasks)}")
    msg = build_checkin_message(outreach_count, jobs_count, interviews, active_projects, overdue_tasks)
    log(f"[friday-checkin] Message:\n{msg}")
    send_telegram(msg)
    log(f"[friday-checkin] Done.")


if __name__ == "__main__":
    main()
