#!/usr/bin/env python3
"""
ideas-structure.py — Domain 3: Ideas OS
Runs nightly via cron. Picks up pending ideas, structures them with Claude Haiku,
sends to Telegram, and updates Google Sheets.
"""

import os
import json
import datetime
import requests
import anthropic
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

WORKSPACE = "/root/.openclaw/workspace"
SHEET_ID = "1o6XXLhpxFVZL5SlDKP8a56Y17brgmD7HWzAGe1Ei4Co"
IDEAS_TAB = "Ideas"
PENDING_FILE = os.path.join(WORKSPACE, "ideas-pending.json")
LOG_FILE = os.path.join(WORKSPACE, "logs/ideas.log")
TELEGRAM_BOT = "8397276417:AAFelaU6_0xyF3ImUNmQ3TqW1erW4HieOY0"
TELEGRAM_CHAT = "8768439197"
CLAUDE_MODEL = "claude-haiku-3-5-20241022"

SYSTEM_PROMPT = """You are helping structure a personal idea for a senior AI product manager who is job searching and building his personal brand.

Given a raw idea, extract:
- WHAT: One clear sentence describing what this idea is
- WHY: Why this matters to him right now (be specific — job search? income? learning? brand?)
- FIRST STEP: The absolute smallest next action. Specific. Under 10 words. Something he could do in 30 minutes.
- EFFORT: Low (< 2 hours), Medium (< 1 day), High (multi-day)
- PRIORITY: High (directly helps job search or income), Medium (brand/learning), Low (nice to have)

Output as JSON: {"what": "...", "why": "...", "first_step": "...", "effort": "...", "priority": "..."}"""


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


def load_pending():
    if not os.path.exists(PENDING_FILE):
        return []
    with open(PENDING_FILE) as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def save_pending(entries):
    with open(PENDING_FILE, "w") as f:
        json.dump(entries, f, indent=2)


def structure_idea(idea_text):
    """Call Claude Haiku to structure the idea. Returns dict."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set")
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": idea_text}],
    )
    raw = message.content[0].text.strip()
    # Parse JSON — strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT}/sendMessage"
    resp = requests.post(
        url,
        json={"chat_id": TELEGRAM_CHAT, "text": text, "parse_mode": "Markdown"},
        timeout=10,
    )
    if resp.status_code != 200:
        log(f"[ideas-structure] Telegram error: {resp.text}")
    else:
        log(f"[ideas-structure] Telegram message sent.")


def build_telegram_message(idea_text, structured):
    # Truncate idea for summary if long
    summary = idea_text if len(idea_text) <= 80 else idea_text[:77] + "..."
    return (
        f'💡 You dropped an idea: "{summary}"\n\n'
        f"Here's how I see it:\n\n"
        f"WHAT: {structured['what']}\n"
        f"WHY: {structured['why']}\n"
        f"FIRST STEP: {structured['first_step']}\n"
        f"EFFORT: {structured['effort']}\n"
        f"PRIORITY: {structured['priority']}\n\n"
        f"Reply 'yes' to activate, 'edit [what to change]' to revise, or 'park' to shelve it."
    )


def find_idea_row(service, idea_text):
    """Find the row index (1-based) of this idea in the Ideas sheet."""
    result = service.spreadsheets().values().get(
        spreadsheetId=SHEET_ID, range=f"{IDEAS_TAB}!A:A"
    ).execute()
    rows = result.get("values", [])
    for i, row in enumerate(rows):
        if row and row[0].strip() == idea_text.strip():
            return i + 1  # 1-based
    return None


def update_sheet_status(service, idea_text, status, first_step=""):
    """Update Status (col B) and optionally First Step (col C) for this idea row."""
    row_num = find_idea_row(service, idea_text)
    if row_num is None:
        log(f"[ideas-structure] Warning: idea not found in sheet, skipping update.")
        return
    now_str = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    updates = [
        {
            "range": f"{IDEAS_TAB}!B{row_num}",
            "values": [[status]],
        },
        {
            "range": f"{IDEAS_TAB}!E{row_num}",
            "values": [[now_str]],
        },
    ]
    if first_step:
        updates.append({
            "range": f"{IDEAS_TAB}!C{row_num}",
            "values": [[first_step]],
        })
    service.spreadsheets().values().batchUpdate(
        spreadsheetId=SHEET_ID,
        body={"valueInputOption": "USER_ENTERED", "data": updates},
    ).execute()
    log(f"[ideas-structure] Sheet updated: row {row_num} → Status={status}")


def main():
    now_str = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    log(f"\n[{now_str}] [ideas-structure] Starting...")

    pending = load_pending()
    unstructured = [e for e in pending if not e.get("structured")]

    if not unstructured:
        log("[ideas-structure] No pending ideas to structure. Exiting.")
        return

    log(f"[ideas-structure] Found {len(unstructured)} unstructured idea(s).")

    creds = get_creds()
    service = build("sheets", "v4", credentials=creds)

    processed = []
    for entry in pending:
        if entry.get("structured"):
            processed.append(entry)
            continue

        idea_text = entry["idea"]
        log(f"[ideas-structure] Structuring: {idea_text[:60]}...")

        try:
            structured = structure_idea(idea_text)
            log(f"[ideas-structure] Got structure: {structured}")

            msg = build_telegram_message(idea_text, structured)
            send_telegram(msg)

            update_sheet_status(
                service, idea_text, "Structured", structured.get("first_step", "")
            )

            entry["structured"] = True
            entry["structure"] = structured
            entry["structured_at"] = now_str
            processed.append(entry)

        except Exception as e:
            log(f"[ideas-structure] Error processing idea: {e}")
            processed.append(entry)  # keep it, retry next time

    save_pending(processed)
    log(f"[ideas-structure] Done.")


if __name__ == "__main__":
    main()
