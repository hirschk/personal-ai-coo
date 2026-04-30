#!/usr/bin/env python3
"""
linkedin-content-prompt.py
Runs Mon/Wed/Fri at 23:00 UTC (6pm EST).
Checks today's memory file for post-worthy content, then sends a Telegram prompt.
"""

import os
import sys
import json
import requests
from datetime import datetime, timezone, timedelta
sys.path.insert(0, os.path.dirname(__file__))
from state import posted_within_days, _load, _save
from dotenv import load_dotenv

# Config
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
WORKSPACE = "/root/.openclaw/workspace"
MEMORY_DIR = os.path.join(WORKSPACE, "memory")
LOG_FILE = os.path.join(WORKSPACE, "logs", "linkedin-content.log")


def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
    }
    resp = requests.post(url, json=payload, timeout=10)
    resp.raise_for_status()
    return resp.json()


def log(msg):
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    line = f"[{timestamp}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception as e:
        print(f"[warn] Could not write to log: {e}", file=sys.stderr)


def extract_post_worthy_content(memory_text):
    """
    Look for anything that reads like an insight, observation, or shareable idea.
    Returns a short summary string if found, or None.
    """
    keywords = [
        "noticed", "learned", "insight", "realized", "discovered",
        "shipped", "launched", "found", "interesting", "idea", "pattern",
        "job", "interview", "application", "recruiting", "role",
        "ai", "product", "pm", "data", "pipeline", "model",
    ]
    lines = memory_text.splitlines()
    candidates = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        lower = stripped.lower()
        if any(kw in lower for kw in keywords):
            candidates.append(stripped)

    if not candidates:
        return None

    # Return the first strong candidate, truncated to ~120 chars
    best = candidates[0]
    if len(best) > 120:
        best = best[:117] + "..."
    return best


def main():
    if posted_within_days("linkedin_post", days=3):
        log("Post already made in last 3 days — skipping prompt.")
        return

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    memory_file = os.path.join(MEMORY_DIR, f"{today}.md")

    found_content = None

    if os.path.exists(memory_file):
        try:
            with open(memory_file, "r") as f:
                memory_text = f.read()
            if memory_text.strip():
                found_content = extract_post_worthy_content(memory_text)
        except Exception as e:
            log(f"Could not read memory file: {e}")

    if found_content:
        message = (
            "Hey — content time 📝\n\n"
            f"You mentioned earlier today: \"{found_content}\"\n\n"
            "Want me to turn that into this week's LinkedIn post?\n\n"
            "Reply 'yes' to use that, or dump something new below "
            "(voice or text, as messy as you want)."
        )
        log(f"Sending prompt with memory hook: {found_content[:60]}...")
    else:
        message = (
            "Hey — content time 📝\n\n"
            "What's something interesting you worked on, learned, or noticed this week? "
            "Voice note or text, as messy as you want."
        )
        log("Sending generic content prompt (no memory hook found).")

    try:
        send_telegram(message)
        # Mark prompt sent so we don't re-fire for 3 days
        data = _load()
        data["linkedin_post"] = {"last_posted": datetime.now(timezone.utc).isoformat()}
        _save(data)
        log("Telegram prompt sent successfully.")
    except Exception as e:
        log(f"ERROR sending Telegram message: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
