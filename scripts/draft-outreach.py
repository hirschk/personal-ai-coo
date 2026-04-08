#!/usr/bin/env python3
"""
draft-outreach.py — Generate outreach draft for a job from jobs-today.json

Usage:
    python3 draft-outreach.py <job_number> [--intro "Mutual Name"]

Examples:
    python3 draft-outreach.py 3                        # auto-selects template
    python3 draft-outreach.py 3 --intro "Sarah Lee"   # uses intro request template
"""

import argparse
import json
import os
import sys
import re
from datetime import datetime
from collections import defaultdict

WORKSPACE = "/root/.openclaw/workspace"


# ── Voice rules loader ────────────────────────────────────────────────────────

def load_voice_rules():
    path = os.path.join(WORKSPACE, "voice_rules.md")
    if not os.path.exists(path):
        return []
    rules = []
    with open(path) as f:
        in_section = False
        for line in f:
            if line.startswith("## Outreach Rules") or line.startswith("## Learned Rules"):
                in_section = True
                continue
            if line.startswith("## ") and in_section:
                in_section = False
            if in_section and line.startswith("- "):
                rules.append(line.strip())
    return rules


# ── Loaders ───────────────────────────────────────────────────────────────────

def load_jobs():
    path = os.path.join(WORKSPACE, "jobs-today.json")
    if not os.path.exists(path):
        print(f"ERROR: jobs-today.json not found at {path}", file=sys.stderr)
        sys.exit(1)
    with open(path) as f:
        data = json.load(f)
    # Support both top_5 and all_scored
    return data.get("all_scored") or data.get("top_5") or []


def load_network():
    """Parse network.md into a dict: company_lower -> list of contact dicts."""
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
    """Return (degree, contact_dict | None). Degree: 1 if 1st-degree PM/insider, else None."""
    key = re.sub(r'\b(inc|llc|ltd|corp|co)\.?\b', '', company_name.lower()).strip()

    # Try exact match first, then substring match
    matches = []
    for net_key, contacts in network.items():
        cleaned_net = re.sub(r'\b(inc|llc|ltd|corp|co)\.?\b', '', net_key).strip()
        if cleaned_net == key or key in cleaned_net or cleaned_net in key:
            matches.extend(contacts)

    if not matches:
        return None, None

    # Prefer PM/product contacts for referral
    for c in matches:
        tl = c["title"].lower()
        if any(x in tl for x in ["product", " pm", "chief", "head of"]):
            return 1, c
    # Then any insider
    return 1, matches[0]


# ── Proof points ──────────────────────────────────────────────────────────────

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
    "biotech": (
        "co-founded Sci-Insights AI — a no-code ML platform for genomic cancer research, "
        "adopted by 4 labs and scaled to $84K ARR"
    ),
    "healthtech": (
        "co-founded Sci-Insights AI — no-code ML platform for genomic cancer research, "
        "adopted by 4 labs"
    ),
    "default": (
        "$23M in revenue impact across 8 engagements — "
        "fintech, AI, biotech, and enterprise — most recently at Hearth (Series B)"
    ),
}

YEARS_EXP = "10"


def pick_proof_point(job: dict) -> str:
    """Pick the most relevant proof point based on job industry/company."""
    industry = (job.get("company_industry") or "").lower()
    company = (job.get("company") or "").lower()
    title = (job.get("title") or "").lower()

    # Check industry first
    for key, proof in PROOF_POINTS.items():
        if key in industry:
            return proof

    # Check company name / title for clues
    for key in ["fintech", "payments", "banking", "ai", "saas", "b2b", "enterprise", "biotech"]:
        if key in company or key in title:
            return PROOF_POINTS[key]

    return PROOF_POINTS["default"]


# ── Template builders ─────────────────────────────────────────────────────────

def build_referral_draft(job: dict, contact: dict) -> str:
    company = job["company"]
    role = job["title"]
    proof = pick_proof_point(job)
    rules = load_voice_rules()
    # Voice rules loaded from voice_rules.md — {len(rules)} rules active

    lines = [
        f"Hey {contact['name'].split()[0]},",
        "",
        f"Hope you're doing well. I noticed {company} is hiring a {role} — thought I'd reach out since you're there.",
        "",
        f"Quick context: I've spent {YEARS_EXP} years building AI/ML products — most recently {proof}. Maps well to what they're looking for.",
        "",
        f"Would you be comfortable putting in a word or referring me? Happy to send a blurb you can forward — whatever's easiest.",
        "",
        "Thanks either way.",
        "Hirsch",
    ]
    return "\n".join(lines)


def build_warm_outreach_draft(job: dict) -> str:
    company = job["company"]
    role = job["title"]
    proof = pick_proof_point(job)
    industry = (job.get("company_industry") or "").lower()
    rules = load_voice_rules()
    # Voice rules loaded from voice_rules.md — {len(rules)} rules active

    # Pick connecting line based on industry
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
        f"I'd love to learn more about the team and what you're solving for. Is there a good way to connect?",
        "",
        "Hirsch",
    ]
    return "\n".join(lines)


def build_intro_request_draft(job: dict, mutual_name: str, target_name: str = "[Target Name]") -> str:
    company = job["company"]
    role = job["title"]
    rules = load_voice_rules()
    # Voice rules loaded from voice_rules.md — {len(rules)} rules active

    lines = [
        f"Hey {mutual_name},",
        "",
        f"Quick one \u2014 I noticed you're connected to {target_name} at {company}. They're hiring a {role} and it looks like a strong fit for my background.",
        "",
        "Any chance you'd be comfortable making an intro? Happy to send a blurb to make it easy.",
        "",
        "Thanks either way.",
        "Hirsch",
    ]
    return "\n".join(lines)


# ── Logger ────────────────────────────────────────────────────────────────────

def log_draft(job: dict, draft: str, template_used: str):
    log_dir = os.path.join(WORKSPACE, "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "outreach-drafts.log")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    separator = "─" * 60
    entry = (
        f"\n{separator}\n"
        f"[{timestamp}] {job['title']} @ {job['company']} | Template: {template_used}\n"
        f"{separator}\n"
        f"{draft}\n"
    )
    with open(log_path, "a") as f:
        f.write(entry)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate outreach draft for a job")
    parser.add_argument("job_number", type=int, help="Job number from today's list (1-based)")
    parser.add_argument("--intro", metavar="MUTUAL_NAME",
                        help="Use intro request template with this mutual connection name")
    args = parser.parse_args()

    jobs = load_jobs()
    if not jobs:
        print("ERROR: No jobs found in jobs-today.json", file=sys.stderr)
        sys.exit(1)

    job_num = args.job_number
    if job_num < 1 or job_num > len(jobs):
        print(f"ERROR: Job #{job_num} out of range (1–{len(jobs)})", file=sys.stderr)
        sys.exit(1)

    job = jobs[job_num - 1]
    print(f"📋 Job #{job_num}: {job['title']} @ {job['company']}", file=sys.stderr)
    if job.get("url"):
        print(f"   {job['url']}", file=sys.stderr)

    network = load_network()

    if args.intro:
        mutual_name = args.intro
        template_used = f"Intro Request (via {mutual_name})"
        draft = build_intro_request_draft(job, mutual_name)
        print(f"\n🤝 Using intro request template via {mutual_name}", file=sys.stderr)
    else:
        degree, contact = find_connection(job["company"], network)
        if degree == 1 and contact:
            template_used = "Referral Request (1st-degree)"
            draft = build_referral_draft(job, contact)
            print(f"\n🔗 Connection found: {contact['name']} ({contact['title']})", file=sys.stderr)
        else:
            template_used = "Warm Outreach (no direct connection)"
            draft = build_warm_outreach_draft(job)
            print(f"\n📬 No connection found — using warm outreach template", file=sys.stderr)

    print(f"📝 Template: {template_used}\n", file=sys.stderr)
    print("─" * 60)
    print(draft)
    print("─" * 60)

    log_draft(job, draft, template_used)
    print(f"\n✅ Draft logged to logs/outreach-drafts.log", file=sys.stderr)


if __name__ == "__main__":
    main()
