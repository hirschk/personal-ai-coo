#!/usr/bin/env python3
"""
recruiter-response.py — Generate a recruiter response draft

Usage:
    python3 recruiter-response.py "Ramp"
    python3 recruiter-response.py "Ramp" "[Name]"   # optionally specify recruiter name

Outputs a clean, copy-paste-ready recruiter response to stdout.
Logs to logs/outreach-drafts.log.
"""

import os
import sys
from datetime import datetime

WORKSPACE = "/root/.openclaw/workspace"


def build_recruiter_response(company: str, recruiter_name: str = "[Name]") -> str:
    first = recruiter_name.split()[0] if recruiter_name != "[Name]" else "[Name]"

    lines = [
        f"Hi {first},",
        "",
        f"Thanks for reaching out. Yes, I'm interested — {company}'s work caught my eye.",
        "",
        "Quick context: I'm a senior AI PM, most recently Head of Product at Hearth (fintech, Series B). "
        "Before that I ran a fractional AI PM studio with $23M in revenue impact across 8 engagements. "
        "I tend to work best in roles with real product scope — owning strategy, roadmap, and a team.",
        "",
        "Happy to connect for a screen and learn more about the role. "
        "What does availability look like on your end?",
        "",
        "Hirsch",
    ]
    return "\n".join(lines)


def log_draft(company: str, draft: str):
    log_dir = os.path.join(WORKSPACE, "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "outreach-drafts.log")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    separator = "─" * 60
    entry = (
        f"\n{separator}\n"
        f"[{timestamp}] Recruiter Response @ {company} | Template: Recruiter Response\n"
        f"{separator}\n"
        f"{draft}\n"
    )
    with open(log_path, "a") as f:
        f.write(entry)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 recruiter-response.py \"Company Name\" [\"Recruiter Name\"]", file=sys.stderr)
        sys.exit(1)

    company = sys.argv[1]
    recruiter_name = sys.argv[2] if len(sys.argv) > 2 else "[Name]"

    draft = build_recruiter_response(company, recruiter_name)

    print(f"📋 Recruiter Response: {company}", file=sys.stderr)
    if recruiter_name != "[Name]":
        print(f"   Recruiter: {recruiter_name}", file=sys.stderr)
    print("", file=sys.stderr)

    print("─" * 60)
    print(draft)
    print("─" * 60)

    log_draft(company, draft)
    print(f"\n✅ Draft logged to logs/outreach-drafts.log", file=sys.stderr)


if __name__ == "__main__":
    main()
