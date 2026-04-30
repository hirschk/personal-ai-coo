#!/usr/bin/env python3
"""
Parse the broken Jobs sheet data and rewrite it cleanly.
Data pattern: pairs of rows per job, duplicated 5x — dedupe and fix columns.
"""

import json, os, re
from google.oauth2 import service_account
from googleapiclient.discovery import build

SHEET_ID = "1o6XXLhpxFVZL5SlDKP8a56Y17brgmD7HWzAGe1Ei4Co"
WORKSPACE = "/root/.openclaw/workspace"
SA_KEY_FILE = os.path.join(WORKSPACE, "config/sterl-sheets-key.json")
SHEETS_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

creds = service_account.Credentials.from_service_account_file(
    SA_KEY_FILE, scopes=SHEETS_SCOPES
)
svc = build("sheets", "v4", credentials=creds)
sheets = svc.spreadsheets()

# ── Fetch raw data ────────────────────────────────────────────────────────────

raw = sheets.values().get(
    spreadsheetId=SHEET_ID,
    range="Jobs!A:J",
    valueRenderOption="UNFORMATTED_VALUE"
).execute().get("values", [])

# Skip header row
data_rows = raw[1:] if raw else []

# ── Parse pairs of rows into job records ─────────────────────────────────────
# Row A (odd): "Company Role Title"  e.g. "Monzo Product Director"
# Row B (even): "Specialization URL priority_score fit_score network_score Network Path status (date)"

def parse_row_b(cells):
    """Parse the data row — all cells joined as one string since gog splits on whitespace."""
    text = " ".join(str(c) for c in cells).strip()

    # Extract URL
    url_match = re.search(r'(https?://\S+)', text)
    url = url_match.group(1) if url_match else ""

    # Split on URL
    if url:
        before_url = text[:text.index(url)].strip()
        after_url = text[text.index(url) + len(url):].strip()
    else:
        before_url = text
        after_url = ""

    specialization = before_url

    # Extract scores (3 numbers after URL)
    score_match = re.findall(r'\b(0\.\d+|\d+\.\d+)\b', after_url)
    priority = score_match[0] if len(score_match) > 0 else ""
    fit      = score_match[1] if len(score_match) > 1 else ""
    network  = score_match[2] if len(score_match) > 2 else ""

    # Extract network path — text in parens after scores
    net_path_match = re.search(r'([A-Z][a-z]+ [A-Z][a-zA-Z]+(?: [A-Z][a-zA-Z]+)* \([^)]+\))', after_url)
    net_path = net_path_match.group(1) if net_path_match else ""

    # Extract status and date
    status_match = re.search(r'\b(new|applied|interviewing|offer|rejected|paused)\b', after_url, re.IGNORECASE)
    status = status_match.group(1).lower() if status_match else "new"

    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', after_url)
    date = date_match.group(1) if date_match else ""

    return specialization, url, priority, fit, network, net_path, status, date

def parse_row_a(cells):
    """First cell or joined cells = 'Company Role'. Split on known company names."""
    text = " ".join(str(c) for c in cells).strip()
    # Try to split: first word(s) = company, rest = role
    # Known companies in this dataset
    known = ["Monzo", "Chime", "Instacart"]
    for co in known:
        if text.startswith(co):
            role = text[len(co):].strip()
            return co, role
    # Fallback: first word = company
    parts = text.split(" ", 1)
    return parts[0], parts[1] if len(parts) > 1 else ""

# Collect all parsed jobs, dedupe by URL
seen_urls = set()
jobs = []

i = 0
while i < len(data_rows) - 1:
    row_a = data_rows[i]
    row_b = data_rows[i + 1]

    # Skip if row_a looks like a data row (contains URL)
    a_text = " ".join(str(c) for c in row_a)
    if "http" in a_text:
        i += 1
        continue

    company, role = parse_row_a(row_a)
    spec, url, priority, fit, network, net_path, status, date = parse_row_b(row_b)

    if url and url not in seen_urls:
        seen_urls.add(url)
        jobs.append([company, role, spec, url, priority, fit, network, net_path, status, date])

    i += 2

print(f"Parsed {len(jobs)} unique jobs:")
for j in jobs:
    print(f"  {j[0]} | {j[1]} | {j[3][:50]}...")

# ── Also append today's Apify results ────────────────────────────────────────

import os, sys
sys.path.insert(0, "/root/.openclaw/workspace")

try:
    with open("/root/.openclaw/workspace/jobs-today.json") as f:
        today = json.load(f)
    for j in today.get("top_5", []):
        if j["url"] not in seen_urls:
            seen_urls.add(j["url"])
            jobs.append([
                j["company"],
                j["title"],
                "",  # no specialization field in Apify results
                j["url"],
                str(j["priority_score"]),
                str(j["fit_score"]),
                str(j["network_score"]),
                j.get("network_path") or "",
                "new",
                j.get("published_at") or "",
            ])
    print(f"Total after merging today's results: {len(jobs)}")
except Exception as e:
    print(f"Could not merge today's results: {e}")

# ── Clear and rewrite Jobs sheet ──────────────────────────────────────────────

# Clear all data
sheets.values().clear(spreadsheetId=SHEET_ID, range="Jobs!A1:Z1000").execute()

# Write headers + data
headers = [["Company", "Role", "Specialization", "URL", "Priority Score", "Fit Score", "Network Score", "Network Path", "Status", "Date Added"]]
sheets.values().update(
    spreadsheetId=SHEET_ID,
    range="Jobs!A1",
    valueInputOption="USER_ENTERED",
    body={"values": headers + jobs}
).execute()

# ── Format ────────────────────────────────────────────────────────────────────

# Get Jobs sheet ID
meta = sheets.get(spreadsheetId=SHEET_ID).execute()
jobs_sid = next(s["properties"]["sheetId"] for s in meta["sheets"] if s["properties"]["title"] == "Jobs")

GREY = {"red": 0.85, "green": 0.85, "blue": 0.85}
GREEN = {"red": 0.78, "green": 0.93, "blue": 0.80}
RED   = {"red": 0.96, "green": 0.79, "blue": 0.78}
YELLOW= {"red": 1.0,  "green": 0.95, "blue": 0.70}

col_widths = [150, 220, 180, 320, 100, 80, 100, 260, 110, 100]

reqs = [
    # Header formatting
    {"repeatCell": {
        "range": {"sheetId": jobs_sid, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": 10},
        "cell": {"userEnteredFormat": {
            "backgroundColor": GREY,
            "textFormat": {"bold": True, "fontFamily": "Arial", "fontSize": 10},
            "verticalAlignment": "MIDDLE",
        }},
        "fields": "userEnteredFormat(backgroundColor,textFormat,verticalAlignment)",
    }},
    # Body font
    {"repeatCell": {
        "range": {"sheetId": jobs_sid, "startRowIndex": 1, "endRowIndex": 500, "startColumnIndex": 0, "endColumnIndex": 10},
        "cell": {"userEnteredFormat": {"textFormat": {"fontFamily": "Arial", "fontSize": 10}}},
        "fields": "userEnteredFormat.textFormat",
    }},
    # Freeze header
    {"updateSheetProperties": {
        "properties": {"sheetId": jobs_sid, "gridProperties": {"frozenRowCount": 1}},
        "fields": "gridProperties.frozenRowCount",
    }},
    # Status dropdown (col 8 = index 8)
    {"setDataValidation": {
        "range": {"sheetId": jobs_sid, "startRowIndex": 1, "endRowIndex": 1000, "startColumnIndex": 8, "endColumnIndex": 9},
        "rule": {
            "condition": {"type": "ONE_OF_LIST", "values": [
                {"userEnteredValue": v} for v in ["new", "applied", "interviewing", "offer", "rejected", "paused"]
            ]},
            "showCustomUi": True, "strict": False,
        },
    }},
]

# Conditional formatting — appended separately to avoid syntax issues inside list
col_ref = chr(36) + "I2"  # dollar-sign + I2

def cf_rule(sid, formula_val, bg):
    return {"addConditionalFormatRule": {"rule": {
        "ranges": [{"sheetId": sid, "startRowIndex": 1, "endRowIndex": 1000,
                    "startColumnIndex": 0, "endColumnIndex": 10}],
        "booleanRule": {
            "condition": {"type": "CUSTOM_FORMULA", "values": [{"userEnteredValue": formula_val}]},
            "format": {"backgroundColor": bg},
        }
    }, "index": 0}}

reqs.append(cf_rule(jobs_sid, f'={col_ref}="offer"', GREEN))
reqs.append(cf_rule(jobs_sid, f'={col_ref}="rejected"', RED))
reqs.append(cf_rule(jobs_sid, f'={col_ref}="interviewing"', YELLOW))

reqs += [  # re-open for col widths below
]

# Column widths
for i, w in enumerate(col_widths):
    reqs.append({"updateDimensionProperties": {
        "range": {"sheetId": jobs_sid, "dimension": "COLUMNS", "startIndex": i, "endIndex": i+1},
        "properties": {"pixelSize": w},
        "fields": "pixelSize",
    }})

sheets.batchUpdate(spreadsheetId=SHEET_ID, body={"requests": reqs}).execute()

print(f"\n✅ Jobs sheet fixed — {len(jobs)} rows, clean columns, formatted.")
print(f"https://docs.google.com/spreadsheets/d/{SHEET_ID}")
