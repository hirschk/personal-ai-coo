#!/usr/bin/env python3
"""
One-time script: load network_matches_outreach CSV into Jobs tab.
Columns: Company | Role | Specialization | URL | Priority Score | Fit Score | Network Score | Network Path | Status | Date Added
"""

import json, os, csv
from datetime import datetime, timezone
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

WORKSPACE = "/root/.openclaw/workspace"
SHEET_ID  = "1o6XXLhpxFVZL5SlDKP8a56Y17brgmD7HWzAGe1Ei4Co"
CSV_PATH  = "/root/.openclaw/media/inbound/network_matches_outreach---d76d7019-6e12-4c4c-80df-08d5afcbf24b.csv"

# Already outreached — mark as applied so morning brief skips them
ALREADY_SENT = {"matas sriubiskis", "ali vira", "austin osborne"}

# Skip — wrong industry
SKIP_COMPANIES = {"hubbell incorporated"}

TODAY = datetime.now(timezone.utc).date().strftime("%Y-%m-%d")

with open(f"{WORKSPACE}/config/gog-token.json") as f:
    tok = json.load(f)
with open(f"{WORKSPACE}/google_client_secret.json") as f:
    secret = json.load(f)
cfg = secret.get("installed") or secret.get("web") or secret
creds = Credentials(
    token=tok.get("token"), refresh_token=tok["refresh_token"],
    token_uri="https://oauth2.googleapis.com/token",
    client_id=cfg["client_id"], client_secret=cfg["client_secret"],
    scopes=["https://www.googleapis.com/auth/spreadsheets"],
)
if creds.expired or not creds.valid:
    creds.refresh(Request())
svc = build("sheets", "v4", credentials=creds).spreadsheets()

# Get existing Jobs to avoid duplicates
existing = svc.values().get(spreadsheetId=SHEET_ID, range="Jobs!A2:J200").execute().get("values", [])
existing_keys = set()
for row in existing:
    if len(row) >= 2:
        existing_keys.add((row[0].strip().lower(), row[1].strip().lower()[:30]))

rows_to_add = []
skipped = []
already_sent = []

with open(CSV_PATH) as f:
    reader = csv.DictReader(f)
    for row in reader:
        company   = row["Company"].strip()
        name      = row["Connection Name"].strip()
        title     = row["Connection Title"].strip()
        url       = row["Connection LinkedIn URL"].strip()
        role      = row["Open Role"].strip()
        message   = row["Message"].strip()

        if company.lower() in SKIP_COMPANIES:
            skipped.append(f"{company} ({name}) — wrong industry")
            continue

        key = (company.lower(), role.lower()[:30])
        if key in existing_keys:
            skipped.append(f"{company} ({name}) — already in Jobs")
            continue

        network_path = f"{name} ({title})"
        status = "outreaching" if name.lower() in ALREADY_SENT else "new"

        if name.lower() in ALREADY_SENT:
            already_sent.append(f"{name} @ {company}")

        # Company | Role | Specialization | URL | Priority | Fit | Network | Network Path | Status | Date Added
        rows_to_add.append([
            company, role, "", "", "", "", "1", network_path, status, TODAY
        ])

if rows_to_add:
    svc.values().append(
        spreadsheetId=SHEET_ID,
        range="Jobs!A:J",
        valueInputOption="USER_ENTERED",
        body={"values": rows_to_add}
    ).execute()
    print(f"Added {len(rows_to_add)} rows to Jobs tab")
else:
    print("Nothing new to add")

if skipped:
    print(f"Skipped ({len(skipped)}): {', '.join(skipped)}")
if already_sent:
    print(f"Marked applied (already outreached): {', '.join(already_sent)}")
