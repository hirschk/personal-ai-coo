#!/usr/bin/env python3
"""
Rebuild Sterl OS Tracker — clean, professional, fully functional
Sheet ID: 1o6XXLhpxFVZL5SlDKP8a56Y17brgmD7HWzAGe1Ei4Co
"""

import json, os
from google.oauth2 import service_account
from googleapiclient.discovery import build

SHEET_ID = "1o6XXLhpxFVZL5SlDKP8a56Y17brgmD7HWzAGe1Ei4Co"
WORKSPACE = "/root/.openclaw/workspace"
SA_KEY_FILE = os.path.join(WORKSPACE, "config/sterl-sheets-key.json")
SHEETS_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# ── Auth ──────────────────────────────────────────────────────────────────────

creds = service_account.Credentials.from_service_account_file(
    SA_KEY_FILE, scopes=SHEETS_SCOPES
)
svc = build("sheets", "v4", credentials=creds)
sheets = svc.spreadsheets()

# ── Helpers ───────────────────────────────────────────────────────────────────

GREY_BG    = {"red": 0.85, "green": 0.85, "blue": 0.85}
GREEN_BG   = {"red": 0.78, "green": 0.93, "blue": 0.80}
RED_BG     = {"red": 0.96, "green": 0.79, "blue": 0.78}
YELLOW_BG  = {"red": 1.0,  "green": 0.95, "blue": 0.70}
ORANGE_BG  = {"red": 1.0,  "green": 0.85, "blue": 0.60}
WHITE_BG   = {"red": 1.0,  "green": 1.0,  "blue": 1.0}
BLACK      = {"red": 0.0,  "green": 0.0,  "blue": 0.0}

def cell_fmt(bold=False, bg=None, font_size=10, halign=None):
    fmt = {
        "textFormat": {"bold": bold, "fontSize": font_size, "fontFamily": "Arial", "foregroundColor": BLACK},
        "backgroundColor": bg or WHITE_BG,
        "verticalAlignment": "MIDDLE",
        "padding": {"top": 4, "bottom": 4, "left": 6, "right": 6},
    }
    if halign:
        fmt["horizontalAlignment"] = halign
    return fmt

def border_all():
    b = {"style": "SOLID", "color": {"red": 0.8, "green": 0.8, "blue": 0.8}}
    return {"top": b, "bottom": b, "left": b, "right": b}

def header_row_req(sheet_id, cols):
    return {
        "repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1,
                      "startColumnIndex": 0, "endColumnIndex": len(cols)},
            "cell": {"userEnteredFormat": cell_fmt(bold=True, bg=GREY_BG)},
            "fields": "userEnteredFormat(textFormat,backgroundColor,verticalAlignment,padding)",
        }
    }

def freeze_req(sheet_id, rows=1, cols=0):
    return {
        "updateSheetProperties": {
            "properties": {"sheetId": sheet_id, "gridProperties": {"frozenRowCount": rows, "frozenColumnCount": cols}},
            "fields": "gridProperties.frozenRowCount,gridProperties.frozenColumnCount",
        }
    }

def col_width_req(sheet_id, col_widths):
    reqs = []
    for i, w in enumerate(col_widths):
        reqs.append({
            "updateDimensionProperties": {
                "range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": i, "endIndex": i+1},
                "properties": {"pixelSize": w},
                "fields": "pixelSize",
            }
        })
    return reqs

def row_height_req(sheet_id, height=28):
    return {
        "updateDimensionProperties": {
            "range": {"sheetId": sheet_id, "dimension": "ROWS", "startIndex": 0, "endIndex": 1},
            "properties": {"pixelSize": height},
            "fields": "pixelSize",
        }
    }

def dropdown_req(sheet_id, start_row, end_row, col, values):
    return {
        "setDataValidation": {
            "range": {"sheetId": sheet_id, "startRowIndex": start_row, "endRowIndex": end_row,
                      "startColumnIndex": col, "endColumnIndex": col+1},
            "rule": {
                "condition": {"type": "ONE_OF_LIST", "values": [{"userEnteredValue": v} for v in values]},
                "showCustomUi": True,
                "strict": False,
            },
        }
    }

def cond_fmt_eq(sheet_id, start_col, end_col, col_check, value, bg):
    """Highlight entire row when a column equals a value."""
    return {
        "addConditionalFormatRule": {
            "rule": {
                "ranges": [{"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": 1000,
                            "startColumnIndex": start_col, "endColumnIndex": end_col}],
                "booleanRule": {
                    "condition": {
                        "type": "CUSTOM_FORMULA",
                        "values": [{"userEnteredValue": f'=${ chr(65+col_check) }2="{value}"'}],
                    },
                    "format": {"backgroundColor": bg},
                },
            },
            "index": 0,
        }
    }

def borders_req(sheet_id, num_cols, num_rows=500):
    return {
        "repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": num_rows,
                      "startColumnIndex": 0, "endColumnIndex": num_cols},
            "cell": {"userEnteredFormat": {"borders": border_all()}},
            "fields": "userEnteredFormat.borders",
        }
    }

def font_req(sheet_id, num_cols, num_rows=500):
    return {
        "repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": num_rows,
                      "startColumnIndex": 0, "endColumnIndex": num_cols},
            "cell": {"userEnteredFormat": {"textFormat": {"fontFamily": "Arial", "fontSize": 10}}},
            "fields": "userEnteredFormat.textFormat",
        }
    }

def rename_sheet_req(sheet_id, name):
    return {
        "updateSheetProperties": {
            "properties": {"sheetId": sheet_id, "title": name},
            "fields": "title",
        }
    }

# ── Get existing sheet IDs ────────────────────────────────────────────────────

meta = sheets.get(spreadsheetId=SHEET_ID).execute()
existing = {s["properties"]["title"]: s["properties"]["sheetId"] for s in meta["sheets"]}
print("Existing sheets:", list(existing.keys()))

# We need: Jobs, Interviews, Outreach, Contacts, KPIs
NEEDED = ["Jobs", "Interviews", "Outreach", "Contacts", "KPIs"]

add_reqs = []
for name in NEEDED:
    if name not in existing:
        add_reqs.append({"addSheet": {"properties": {"title": name}}})

if add_reqs:
    r = sheets.batchUpdate(spreadsheetId=SHEET_ID, body={"requests": add_reqs}).execute()
    # Refresh
    meta = sheets.get(spreadsheetId=SHEET_ID).execute()
    existing = {s["properties"]["title"]: s["properties"]["sheetId"] for s in meta["sheets"]}

IDS = {name: existing[name] for name in NEEDED}
print("Sheet IDs:", IDS)

# ── Write headers ─────────────────────────────────────────────────────────────

HEADERS = {
    "Jobs":       ["Company", "Role", "URL", "Priority Score", "Fit Score", "Network Score", "Network Path", "Status", "Date Added"],
    "Interviews": ["Company", "Role", "Stage", "Date", "Status", "Notes", "Next Action", "Prep Done"],
    "Outreach":   ["Date", "Name", "Company", "Channel", "Message Type", "Status", "Follow-Up Date", "Notes"],
    "Contacts":   ["Name", "Company", "Title", "LinkedIn URL", "Relevance", "Status", "Added Date", "Notes"],
    "KPIs":       ["Week", "Applications Sent", "Interviews Booked", "Outreach Sent", "Replies Received", "Active Conversations", "Top Opportunity"],
}

batch_data = []
for sheet_name, headers in HEADERS.items():
    batch_data.append({
        "range": f"{sheet_name}!A1",
        "values": [headers],
    })

sheets.values().batchUpdate(
    spreadsheetId=SHEET_ID,
    body={"valueInputOption": "USER_ENTERED", "data": batch_data}
).execute()
print("Headers written.")

# ── KPIs formulas ─────────────────────────────────────────────────────────────

kpi_rows = []
from datetime import datetime, timedelta
today = datetime.today()
monday = today - timedelta(days=today.weekday())
for i in range(6):
    week_start = monday - timedelta(weeks=5-i)
    week_label = week_start.strftime("Week of %b %d")
    kpi_rows.append([week_label, "", "", "", "", "", ""])

kpi_rows.append(["TOTAL",
    f"=COUNTA(Interviews!A2:A)",
    f"=COUNTA(Interviews!A2:A)",
    f"=COUNTA(Outreach!A2:A)",
    f'=COUNTIF(Outreach!F2:F,"Replied")',
    f'=COUNTIF(Interviews!E2:E,"Pending")+COUNTIF(Interviews!E2:E,"Scheduled")',
    "",
])

sheets.values().update(
    spreadsheetId=SHEET_ID,
    range="KPIs!A2",
    valueInputOption="USER_ENTERED",
    body={"values": kpi_rows}
).execute()

# ── Seed existing data ────────────────────────────────────────────────────────

sheets.values().update(
    spreadsheetId=SHEET_ID,
    range="Interviews!A2",
    valueInputOption="USER_ENTERED",
    body={"values": [
        ["Ramp", "Product Manager", "Recruiter Screen", "2026-04-08", "Pending", "Referral via Jason Li (Design Director)", "Send thank you after call", "FALSE"],
        ["Phoenix Technologies", "Senior Product Manager", "CPO Interview (Round 2)", "2026-04-08", "Pending", "Ecomm platform", "Prep product case", "FALSE"],
    ]}
).execute()

sheets.values().update(
    spreadsheetId=SHEET_ID,
    range="Outreach!A2",
    valueInputOption="USER_ENTERED",
    body={"values": [
        ["2026-04-07", "James Chiu", "Cedar", "LinkedIn", "Referral request", "Sent", "", "BrainStation opener; Guestlogix ML reco angle"],
    ]}
).execute()

sheets.values().update(
    spreadsheetId=SHEET_ID,
    range="Contacts!A2",
    valueInputOption="USER_ENTERED",
    body={"values": [
        ["Jason Li", "Ramp", "Design Director", "", "Referred resume", "Active", "2026-04-07", "Put resume top of pile for PM role"],
        ["James Chiu", "Cedar", "Director, Product Design", "https://www.linkedin.com/in/james-chiu", "DM sent re: Principal PM AI/ML", "Warm", "2026-04-07", ""],
    ]}
).execute()

print("Data seeded.")

# ── Formatting requests ───────────────────────────────────────────────────────

COL_WIDTHS = {
    "Jobs":       [160, 200, 280, 100, 80, 100, 220, 110, 100],
    "Interviews": [160, 200, 160, 100, 100, 250, 200, 90],
    "Outreach":   [100, 140, 160, 110, 140, 120, 120, 250],
    "Contacts":   [160, 160, 180, 240, 200, 90, 100, 220],
    "KPIs":       [160, 140, 140, 120, 140, 160, 220],
}

STATUS_DROPDOWNS = {
    "Jobs":       (7, ["New", "Applied", "Interviewing", "Offer", "Rejected", "Paused"]),
    "Interviews": (4, ["Pending", "Scheduled", "Completed", "Passed", "Failed"]),
    "Outreach":   (5, ["Draft", "Sent", "Replied", "No Response", "Meeting Booked"]),
    "Contacts":   (5, ["Active", "Warm", "Cold", "Converted"]),
}

STAGE_DROPDOWN = ["Recruiter Screen", "Hiring Manager", "Technical", "Case Study", "CPO/Executive", "Final Round", "Offer"]
CHANNEL_DROPDOWN = ["LinkedIn", "Email", "Intro/Referral", "Event"]

reqs = []

for name in NEEDED:
    sid = IDS[name]
    ncols = len(HEADERS[name])
    reqs.append(header_row_req(sid, HEADERS[name]))
    reqs.append(freeze_req(sid))
    reqs.append(row_height_req(sid))
    reqs.append(borders_req(sid, ncols))
    reqs.append(font_req(sid, ncols))
    reqs += col_width_req(sid, COL_WIDTHS[name])

# Dropdowns
for name, (col, values) in STATUS_DROPDOWNS.items():
    reqs.append(dropdown_req(IDS[name], 1, 1000, col, values))

reqs.append(dropdown_req(IDS["Interviews"], 1, 1000, 2, STAGE_DROPDOWN))
reqs.append(dropdown_req(IDS["Outreach"], 1, 1000, 3, CHANNEL_DROPDOWN))

# Conditional formatting — Jobs (col 7 = Status, 0-indexed)
reqs.append(cond_fmt_eq(IDS["Jobs"], 0, 9, 7, "Offer", GREEN_BG))
reqs.append(cond_fmt_eq(IDS["Jobs"], 0, 9, 7, "Rejected", RED_BG))
reqs.append(cond_fmt_eq(IDS["Jobs"], 0, 9, 7, "Interviewing", YELLOW_BG))

# Conditional formatting — Interviews
reqs.append(cond_fmt_eq(IDS["Interviews"], 0, 8, 4, "Passed", GREEN_BG))
reqs.append(cond_fmt_eq(IDS["Interviews"], 0, 8, 4, "Failed", RED_BG))
reqs.append(cond_fmt_eq(IDS["Interviews"], 0, 8, 4, "Scheduled", YELLOW_BG))

# Conditional formatting — Outreach follow-up date overdue
reqs.append({
    "addConditionalFormatRule": {
        "rule": {
            "ranges": [{"sheetId": IDS["Outreach"], "startRowIndex": 1, "endRowIndex": 1000,
                        "startColumnIndex": 6, "endColumnIndex": 7}],
            "booleanRule": {
                "condition": {
                    "type": "CUSTOM_FORMULA",
                    "values": [{"userEnteredValue": '=AND(G2<TODAY(),G2<>"",F2<>"Replied",F2<>"Meeting Booked")'}],
                },
                "format": {"backgroundColor": RED_BG},
            },
        },
        "index": 0,
    }
})

sheets.batchUpdate(spreadsheetId=SHEET_ID, body={"requests": reqs}).execute()
print("Formatting applied.")
print(f"\n✅ Done: https://docs.google.com/spreadsheets/d/{SHEET_ID}")
