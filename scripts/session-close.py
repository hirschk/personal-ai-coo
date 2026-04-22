#!/usr/bin/env python3
"""
Sterl Session Close — nightly at 11pm EST (04:00 UTC).
Writes end-of-day snapshot to memory/YYYY-MM-DD.md and updates MEMORY.md last-run line.
Cron: 0 4 * * * python3 /root/.openclaw/workspace/scripts/session-close.py >> /root/.openclaw/workspace/logs/session-close.log 2>&1
"""
import json, os, re, subprocess, sys
from datetime import datetime, timezone
from google.oauth2 import service_account
from googleapiclient.discovery import build

WORKSPACE   = "/root/.openclaw/workspace"
SHEET_ID    = "1o6XXLhpxFVZL5SlDKP8a56Y17brgmD7HWzAGe1Ei4Co"
MEMORY_FILE = os.path.join(WORKSPACE, "MEMORY.md")
MEMORY_DIR  = os.path.join(WORKSPACE, "memory")
SA_KEY_FILE = os.path.join(WORKSPACE, "config/sterl-sheets-key.json")
SHEETS_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

def get_creds():
    return service_account.Credentials.from_service_account_file(
        SA_KEY_FILE, scopes=SHEETS_SCOPES
    )

def git_commits_today(date_str):
    try:
        r = subprocess.run(["git","-C",WORKSPACE,"log","--oneline",f"--since={date_str}T00:00:00"],
            capture_output=True, text=True)
        return r.stdout.strip().splitlines()
    except: return []

def cron_activity_today():
    logs = {"job-discovery":"logs/job-discovery.log","followup-sequence":"logs/followup-sequence.log",
            "gmail-reply-check":"logs/gmail-reply-check.log","afternoon-checkin":"logs/afternoon-checkin.log",
            "linkedin-content":"logs/linkedin-content.log","ideas-structure":"logs/ideas.log",
            "friday-checkin":"logs/friday-checkin.log"}
    today = datetime.now(timezone.utc).date()
    return [n for n,p in logs.items() if os.path.exists(os.path.join(WORKSPACE,p)) and
            datetime.fromtimestamp(os.path.getmtime(os.path.join(WORKSPACE,p)),tz=timezone.utc).date()==today]

def pipeline_snapshot():
    try:
        svc = build("sheets","v4",credentials=get_creds()).spreadsheets()
        today = datetime.now(timezone.utc).date()
        rows = svc.values().get(spreadsheetId=SHEET_ID,range="Interviews!A2:H100").execute().get("values",[])
        interviews = [f"{r[0]} — {r[1]} ({r[2]})" for r in rows
                      if len(r)>=5 and r[4] not in ("Completed","Passed","Failed")]
        rows2 = svc.values().get(spreadsheetId=SHEET_ID,range="Outreach!A2:H100").execute().get("values",[])
        overdue = []
        for r in rows2:
            if len(r)<6 or r[5] in ("Replied","Meeting Booked","Stale"): continue
            if r[5]=="Sent" and r[0]:
                try:
                    days=(today-datetime.strptime(r[0],"%Y-%m-%d").date()).days
                    if days>=3: overdue.append(f"{r[1]} @ {r[2]} ({days}d)")
                except: pass
        return interviews, overdue
    except Exception as e:
        print(f"Pipeline snapshot failed: {e}")
        return [], []

def update_memory_lastrun(date_str, summary):
    try:
        with open(MEMORY_FILE) as f: mem = f.read()
        entry = f"Last session-close: {date_str} — {summary}"
        if "Last session-close:" in mem:
            mem = re.sub(r"Last session-close:.*", entry, mem)
        else:
            mem = mem.rstrip() + f"\n\n## Last Run\n{entry}\n"
        with open(MEMORY_FILE,"w") as f: f.write(mem)
    except Exception as e:
        print(f"MEMORY.md update failed: {e}")

def main():
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    print(f"[{now.isoformat()}] session-close starting")

    commits  = git_commits_today(date_str)
    crons    = cron_activity_today()
    interviews, overdue = pipeline_snapshot()

    os.makedirs(MEMORY_DIR, exist_ok=True)
    daily_path = os.path.join(MEMORY_DIR, f"{date_str}.md")
    with open(daily_path, "a") as f:
        f.write(f"\n---\n## End-of-day snapshot — {now.strftime('%H:%M UTC')}\n\n")
        f.write(f"- Commits today: {len(commits)}\n")
        f.write(f"- Crons that ran: {', '.join(crons) if crons else 'none'}\n")
        if interviews: f.write(f"- Active interviews: {', '.join(interviews)}\n")
        if overdue: f.write(f"- Overdue outreach: {', '.join(overdue)}\n")

    summary = f"{len(commits)} commits, {len(crons)} crons ran, {len(interviews)} active interviews"
    update_memory_lastrun(date_str, summary)
    print(f"Done. {summary}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
