#!/usr/bin/env python3
"""
show-drafts.py — Generate outreach drafts for today's top 5 jobs and send via Telegram.

Usage:
    python3 show-drafts.py

Loads jobs-today.json, generates appropriate outreach draft for each of the top 5 jobs
(referral if network match, warm outreach if not), and sends all 5 in one Telegram message.
"""

import json
import os
import re
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime
from dotenv import load_dotenv

WORKSPACE        = "/root/.openclaw/workspace"
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

YEARS_EXP = "10"

PROOF_POINTS = {
    "fintech": (
        "$2.2M ARR opportunity identified and unlocked in 3 days (Hearth, via Claude Code), "
        "and a neobank launched in 4 months to 50K MAUs"
    ),
    "payments": (
        "$2.2M ARR unlocked in 3 days at Hearth (fintech, Series B) "
        "and a 3-in-1 neobank scaled to 50K MAUs"
    ),
    "neobank": (
        "built a 3-in-1 neobank (credit card + savings + life insurance) "
        "from 0→50K MAUs in 4 months"
    ),
    "banking": (
        "neobank launched in 4 months to 50K MAUs; "
        "$2.2M ARR opportunity unlocked at Hearth in 3 days"
    ),
    "ai": (
        "used Claude Code to identify a $2.2M ARR opportunity in 3 days, "
        "and shipped AI chatbots, LLM tools, and ML recommendation engines since 2019"
    ),
    "artificial intelligence": (
        "shipping with LLMs and agentic AI since 2019 — chatbots, recommendation engines, "
        "and a $2.2M ARR unlock in 3 days via Claude Code"
    ),
    "machine learning": (
        "led an ML recommendation engine at Guestlogix across 6 airline partners "
        "and built a no-code ML platform for cancer researchers at Sci-Insights"
    ),
    "saas": (
        "$23M in revenue impact across 8 engagements, "
        "most recently unlocking $2.2M ARR in 3 days at Hearth"
    ),
    "b2b": (
        "$23M in revenue impact across 8 B2B and B2B2C engagements — "
        "from $13M audit automation at Deloitte to $9.6M ACV at Guestlogix"
    ),
    "enterprise": (
        "led a 13-person team at Deloitte Ventures and took an audit automation product "
        "from concept to $13M, hitting 8 consecutive board milestones"
    ),
    "default": (
        "$23M in revenue impact across 8 engagements — "
        "fintech, AI, biotech, and enterprise — most recently at Hearth (Series B)"
    ),
}


def pick_proof_point(job: dict) -> str:
    industry = (job.get("company_industry") or "").lower()
    company  = (job.get("company") or "").lower()
    title    = (job.get("title") or "").lower()

    for key, proof in PROOF_POINTS.items():
        if key in industry:
            return proof

    for key in ["fintech", "payments", "banking", "ai", "saas", "b2b", "enterprise"]:
        if key in company or key in title:
            return PROOF_POINTS[key]

    return PROOF_POINTS["default"]


def load_jobs():
    path = os.path.join(WORKSPACE, "jobs-today.json")
    if not os.path.exists(path):
        print(f"ERROR: jobs-today.json not found at {path}", file=sys.stderr)
        sys.exit(1)
    with open(path) as f:
        data = json.load(f)
    jobs = data.get("top_5") or data.get("all_scored") or []
    return jobs[:5]


def load_network():
    companies = defaultdict(list)
    path = os.path.join(WORKSPACE, "network.md")
    try:
        with open(path) as f:
            for line in f:
                if not line.startswith("|"):
                    continue
                parts = [p.strip() for p in line.split("|")[1:-1]]
                if len(parts) < 3:
                    continue
                name, company, title = parts[0], parts[1], parts[2]
                if not company or company in ("Company", "---") or "---" in name or name == "Name":
                    continue
                companies[company.lower()].append({
                    "name": name, "title": title, "company": company,
                })
    except Exception as e:
        print(f"WARNING: Could not load network.md: {e}", file=sys.stderr)
    return companies


def find_connection(company_name: str, network: dict):
    key = re.sub(r'\b(inc|llc|ltd|corp|co)\.?\b', '', company_name.lower()).strip()
    matches = []
    for net_key, contacts in network.items():
        cleaned_net = re.sub(r'\b(inc|llc|ltd|corp|co)\.?\b', '', net_key).strip()
        if cleaned_net == key or key in cleaned_net or cleaned_net in key:
            matches.extend(contacts)

    if not matches:
        return None, None

    for c in matches:
        tl = c["title"].lower()
        if any(x in tl for x in ["product", " pm", "chief", "head of"]):
            return 1, c
    return 1, matches[0]


def build_referral_draft(job: dict, contact: dict) -> str:
    company = job["company"]
    role    = job["title"]
    proof   = pick_proof_point(job)
    first   = contact["name"].split()[0]

    lines = [
        f"Hey {first},",
        "",
        f"Hope you're doing well. I noticed {company} is hiring a {role} — thought I'd reach out since you're there.",
        "",
        f"Quick context: I've spent {YEARS_EXP} years building AI/ML products — most recently {proof}. Maps well to what they're looking for.",
        "",
        "Would you be comfortable putting in a word or referring me? Happy to send a blurb you can forward — whatever's easiest.",
        "",
        "Thanks either way.",
        "Hirsch",
    ]
    return "\n".join(lines)


def build_warm_outreach_draft(job: dict) -> str:
    company  = job["company"]
    role     = job["title"]
    proof    = pick_proof_point(job)
    industry = (job.get("company_industry") or "").lower()

    if "fintech" in industry or "finance" in industry or "payments" in industry:
        connect = f"Most of my recent work has been at the intersection of AI and fintech, which is why {company}'s approach stood out."
    elif "ai" in industry or "machine learning" in industry:
        connect = f"I've been shipping with LLMs and agentic AI since 2019, so the work {company} is doing maps well to my background."
    elif "enterprise" in industry or "b2b" in industry:
        connect = f"I've built revenue-generating products at enterprise scale — Deloitte, Guestlogix — so the B2B angle at {company} is familiar territory."
    else:
        connect = f"My background spans AI, fintech, and 0→1 launches, which feels relevant to what {company} is building."

    lines = [
        "Hi [Name],",
        "",
        f"I came across {company}'s open {role} role and it caught my attention.",
        "",
        f"I'm a senior AI PM with {YEARS_EXP} years building data-heavy products — {proof}. {connect}",
        "",
        "I'd love to learn more about the team and what you're solving for. Is there a good way to connect?",
        "",
        "Hirsch",
    ]
    return "\n".join(lines)


def send_telegram(text):
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


def main():
    jobs = load_jobs()
    if not jobs:
        print("ERROR: No jobs in jobs-today.json", file=sys.stderr)
        sys.exit(1)

    network = load_network()
    today_str = datetime.now().strftime("%b %d, %Y")

    sections = [f"📝 *Outreach Drafts — {today_str}*\n"]

    for i, job in enumerate(jobs, 1):
        title   = job.get("title", "Unknown Role")
        company = job.get("company", "Unknown Company")

        degree, contact = find_connection(company, network)
        if degree == 1 and contact:
            draft = build_referral_draft(job, contact)
            note  = f"_(referral via {contact['name']})_"
        else:
            draft = build_warm_outreach_draft(job)
            note  = "_(warm outreach)_"

        sections.append(f"*{i}. {title} @ {company}* {note}")
        sections.append("```")
        sections.append(draft)
        sections.append("```")
        sections.append("")

    message = "\n".join(sections).strip()

    # Telegram has a 4096-char limit — truncate gracefully if needed
    if len(message) > 4000:
        message = message[:3990] + "\n...(truncated)"

    print(f"Sending {len(jobs)} outreach drafts to Telegram...")
    send_telegram(message)
    print("✅ Drafts sent.")


if __name__ == "__main__":
    main()
