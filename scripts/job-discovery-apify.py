#!/usr/bin/env python3
"""
Sterl Job Discovery — Apify LinkedIn Jobs Scraper
Uses official apify-client .call() — handles async polling automatically.
Runs: Mon/Wed/Fri 11am EST via cron
"""

import json
import os
import sys
import urllib.request
import urllib.parse
import re
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import difflib

from apify_client import ApifyClient
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

APIFY_TOKEN      = os.environ.get("APIFY_API_TOKEN", "YOUR_APIFY_TOKEN_HERE")
TELEGRAM_TOKEN   = "REDACTED"
TELEGRAM_CHAT_ID = "8768439197"
WORKSPACE        = "/root/.openclaw/workspace"
SHEET_ID         = "1o6XXLhpxFVZL5SlDKP8a56Y17brgmD7HWzAGe1Ei4Co"
GOG_TOKEN_FILE   = os.path.join(WORKSPACE, "config/gog-token.json")

# Job title terms that indicate non-PM roles — filter before scoring
EXCLUDE_TITLES = {
    "marketing", "product marketing", "director of product marketing",
    "growth marketing", "brand", "sales", "account executive",
    "account manager", "customer success", "solutions engineer",
    "data engineer", "software engineer", "frontend", "backend",
    "devops", "designer", "ux designer", "ui designer",
    "recruiter", "talent", "hr ", "finance", "legal", "operations manager",
    "office manager", "executive assistant",
}

# Companies to exclude from results (staffing firms, generic placeholders)
CONFIDENTIAL_BLOCKLIST = {
    "confidential jobs", "confidential", "confidential company",
    "undisclosed", "anonymous",
}

# Generic strings that should never fuzzy-match as network connections
FUZZY_BLOCKLIST = {
    "confidential", "staffing", "recruiting", "consulting",
}

TITLES = [
    "Head of Product",
    "Director of Product",
    "AI Product Manager",
    "Lead Product Manager",
    "Senior Product Manager",
]

TARGET_LOCATIONS = ["austin", "miami", "los angeles", "new york", "san francisco",
                    "remote", "hybrid", "anywhere"]

TARGET_ROLES = {
    "head of product":           1.0,
    "head of ai product":        1.0,
    "vp product":                0.95,
    "vp of product":             0.95,
    "director of product":       0.90,
    "director product":          0.90,
    "ai product manager":        0.85,
    "lead product manager":      0.80,
    "senior product manager":    0.70,
    "group product manager":     0.70,
    "principal product manager": 0.65,
    "staff product manager":     0.65,
}

TARGET_INDUSTRIES = {
    "fintech": 1.0, "financial technology": 1.0, "payments": 0.9,
    "neobank": 0.9, "banking": 0.8,
    "ai": 1.0, "artificial intelligence": 1.0, "machine learning": 0.9,
    "llm": 0.9, "generative": 0.85, "agentic": 0.85,
    "saas": 0.7, "b2b": 0.6,
}

# ── Network ───────────────────────────────────────────────────────────────────

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
                    "name": name, "title": title, "company": company
                })
    except Exception as e:
        print(f"  ⚠ Network error: {e}", file=sys.stderr)
    return companies

def fuzzy_match(job_company, network):
    key = re.sub(r'\b(inc|llc|ltd|corp|co)\.?\b', '', job_company.lower()).strip()
    if key in FUZZY_BLOCKLIST:
        return None, []
    best_r, best_k = 0, None
    for k in network:
        if k in FUZZY_BLOCKLIST:
            continue
        r = difflib.SequenceMatcher(None, key, k).ratio()
        if r > best_r:
            best_r, best_k = r, k
    if best_r >= 0.80:  # raised from 0.70 to cut false positives like Iterable/Litera
        return best_k, network[best_k]
    return None, []

# ── Scoring ───────────────────────────────────────────────────────────────────

def score_fit(title, description, company_industry=""):
    tl = title.lower()
    dl = (description or "").lower() + " " + (company_industry or "").lower()
    role     = max((w for kw, w in TARGET_ROLES.items() if kw in tl), default=0.0)
    industry = max((w for kw, w in TARGET_INDUSTRIES.items() if kw in dl or kw in tl), default=0.0)
    seniority = 0.3 if any(x in tl for x in ["junior", "associate", "entry"]) else 0.9
    return round(min(0.5 * role + 0.3 * industry + 0.2 * seniority, 1.0), 2)

def score_recency(posted_at):
    if not posted_at:
        return 0.5
    try:
        dt = datetime.fromisoformat(posted_at.replace("Z", "+00:00"))
        days = (datetime.now(timezone.utc) - dt).total_seconds() / 86400
    except:
        return 0.5
    if days < 2:  return 1.0
    if days < 4:  return 0.8
    if days < 7:  return 0.5
    if days < 14: return 0.2
    return 0.0

def score_network(contacts):
    if not contacts:
        return 0.0, None
    for c in contacts:
        if any(x in c["title"].lower() for x in ["product", " pm", "chief"]):
            return 1.0, f"{c['name']} ({c['title']} at {c['company']})"
    for c in contacts:
        if any(x in c["title"].lower() for x in ["recruit", "talent", "hr", "people"]):
            return 0.8, f"{c['name']} (Recruiter at {c['company']})"
    return 0.6, f"{contacts[0]['name']} ({contacts[0]['title']})"

def is_pm_role(title: str) -> bool:
    """Return False if the title looks like a non-PM role.

    'product operations' and 'product analyst' are intentionally allowed.
    """
    tl = title.lower()
    # Never exclude roles that are clearly PM-adjacent
    if "product operations" in tl or "product analyst" in tl:
        return True
    for term in EXCLUDE_TITLES:
        if term in tl:
            return False
    return True

# ── Filter + score ────────────────────────────────────────────────────────────

def location_ok(item):
    loc = (item.get("location") or "").lower()
    emp = (item.get("employmentType") or "").lower()
    if "remote" in loc or "remote" in emp or "hybrid" in loc or "hybrid" in emp:
        return True
    return any(tl in loc for tl in TARGET_LOCATIONS)

def is_recent_48h(item):
    pub = item.get("postedAt") or item.get("publishedAt") or item.get("datePosted")
    if not pub:
        return True
    try:
        dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt) <= timedelta(hours=48)
    except:
        return True

def process(items, network):
    filtered = [j for j in items if location_ok(j) and is_recent_48h(j)]
    print(f"  {len(items)} total → {len(filtered)} after location + 48h filter")

    seen, scored = set(), []
    for job in filtered:
        # Skip confidential/anonymous companies — unactionable
        if (job.get("companyName") or "").lower().strip() in CONFIDENTIAL_BLOCKLIST:
            continue
        title   = job.get("title") or ""

        # Skip non-PM roles before scoring
        if not is_pm_role(title):
            continue
        company = job.get("companyName") or ""
        desc    = job.get("descriptionText") or ""
        url     = job.get("link") or job.get("applyUrl") or ""
        loc     = job.get("location") or ""
        pub     = job.get("postedAt") or job.get("publishedAt")
        co_ind  = job.get("companyIndustry") or ""

        if not title or not company:
            continue
        key = f"{title.lower()}|{company.lower()}"
        if key in seen:
            continue
        seen.add(key)

        fs = score_fit(title, desc, co_ind)
        rs = score_recency(pub)
        _, contacts = fuzzy_match(company, network)
        ns, path = score_network(contacts)
        priority = round(0.4 * fs + 0.4 * ns + 0.2 * rs, 2)

        scored.append({
            "title": title, "company": company, "location": loc,
            "url": url, "published_at": pub,
            "fit_score": fs, "network_score": ns,
            "recency_score": rs, "priority_score": priority,
            "network_path": path, "company_industry": co_ind,
        })

    return sorted(scored, key=lambda x: x["priority_score"], reverse=True)

# ── Telegram ──────────────────────────────────────────────────────────────────

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())

def sheets_client():
    """Return authenticated Sheets service, or None if token not available."""
    try:
        with open(GOG_TOKEN_FILE) as f:
            tok = json.load(f)
        with open(os.path.join(WORKSPACE, "google_client_secret.json")) as f:
            secret = json.load(f)
        cfg = secret.get("installed") or secret.get("web") or secret
        creds = Credentials(
            token=None,
            refresh_token=tok["refresh_token"],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=cfg["client_id"],
            client_secret=cfg["client_secret"],
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        return build("sheets", "v4", credentials=creds).spreadsheets()
    except Exception as e:
        print(f"  ⚠ Sheets auth failed: {e}", file=sys.stderr)
        return None

def get_unactioned_jobs():
    """Pull Jobs sheet rows with status 'new' — not yet outreached."""
    svc = sheets_client()
    if not svc:
        return []
    try:
        result = svc.values().get(
            spreadsheetId=SHEET_ID,
            range="Jobs!A2:J100"
        ).execute()
        rows = result.get("values", [])
        unactioned = []
        for row in rows:
            if len(row) < 9: continue
            company, role, status = row[0], row[1], row[8] if len(row) > 8 else "new"
            url = row[3] if len(row) > 3 else ""
            score = row[4] if len(row) > 4 else ""
            if status.lower() == "new":
                unactioned.append({"company": company, "role": role, "url": url, "score": score})
        return unactioned
    except Exception as e:
        print(f"  ⚠ Unactioned jobs fetch failed: {e}", file=sys.stderr)
        return []

def get_followups():
    """Pull Outreach rows where follow-up is due and status is not resolved."""
    svc = sheets_client()
    if not svc:
        return []
    try:
        result = svc.values().get(
            spreadsheetId=SHEET_ID,
            range="Outreach!A2:H100"
        ).execute()
        rows = result.get("values", [])
        today = datetime.now(timezone.utc).date()
        due = []
        for row in rows:
            if len(row) < 6:
                continue
            date, name, company, channel, msg_type, status = row[0], row[1], row[2], row[3], row[4], row[5]
            followup_date = row[6] if len(row) > 6 else ""
            if status in ("Replied", "Meeting Booked"):
                continue
            # Flag if sent and no reply after 3 days
            if status == "Sent" and date:
                try:
                    sent = datetime.strptime(date, "%Y-%m-%d").date()
                    if (today - sent).days >= 3:
                        due.append({"name": name, "company": company, "status": status,
                                    "sent": date, "days_ago": (today - sent).days})
                        continue
                except:
                    pass
            # Flag if explicit follow-up date has passed
            if followup_date:
                try:
                    fdate = datetime.strptime(followup_date, "%Y-%m-%d").date()
                    if fdate <= today and status not in ("Replied", "Meeting Booked"):
                        due.append({"name": name, "company": company, "status": status,
                                    "sent": date, "days_ago": (today - fdate).days})
                except:
                    pass
        return due
    except Exception as e:
        print(f"  ⚠ Outreach fetch failed: {e}", file=sys.stderr)
        return []

def get_weekly_outreach_count():
    """Count outreach messages sent this week (Monday to today) with actionable status."""
    svc = sheets_client()
    if not svc:
        return 0
    try:
        result = svc.values().get(
            spreadsheetId=SHEET_ID,
            range="Outreach!A2:H100"
        ).execute()
        rows = result.get("values", [])
        today = datetime.now(timezone.utc).date()
        monday = today - timedelta(days=today.weekday())  # most recent Monday
        count = 0
        for row in rows:
            if len(row) < 6:
                continue
            date_str = row[0]
            status = row[5] if len(row) > 5 else ""
            if status not in ("Sent", "Replied", "Meeting Booked"):
                continue
            try:
                sent_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                if monday <= sent_date <= today:
                    count += 1
            except:
                pass
        return count
    except Exception as e:
        print(f"  ⚠ Weekly outreach count failed: {e}", file=sys.stderr)
        return 0


def get_upcoming_interviews():
    """Pull interviews in the next 7 days."""
    svc = sheets_client()
    if not svc:
        return []
    try:
        result = svc.values().get(
            spreadsheetId=SHEET_ID,
            range="Interviews!A2:H100"
        ).execute()
        rows = result.get("values", [])
        today = datetime.now(timezone.utc).date()
        upcoming = []
        for row in rows:
            if len(row) < 5:
                continue
            company, role, stage, date_str, status = row[0], row[1], row[2], row[3], row[4]
            notes = row[5] if len(row) > 5 else ""
            if status in ("Completed", "Passed", "Failed"):
                continue
            try:
                idate = datetime.strptime(date_str, "%Y-%m-%d").date()
                days_away = (idate - today).days
                if -1 <= days_away <= 7:  # yesterday through next 7 days
                    upcoming.append({"company": company, "role": role, "stage": stage,
                                     "date": date_str, "days_away": days_away, "notes": notes})
            except:
                pass
        return sorted(upcoming, key=lambda x: x["days_away"])
    except Exception as e:
        print(f"  ⚠ Interviews fetch failed: {e}", file=sys.stderr)
        return []

def format_brief(top5, total_scraped, total_filtered):
    date_str = datetime.now().strftime("%a, %b %d")
    lines = [
        f"🎯 *Job Brief — {date_str}*",
        f"_{total_scraped} scraped → {total_filtered} matched → top {len(top5)} below_\n",
    ]
    for i, j in enumerate(top5, 1):
        lines.append(f"*{i}. {j['title']}* @ {j['company']}")
        if j["location"]:
            lines.append(f"   📍 {j['location']}")
        lines.append(f"   Score: `{j['priority_score']}` (fit {j['fit_score']} · net {j['network_score']} · rec {j['recency_score']})")
        if j["network_path"]:
            lines.append(f"   🔗 {j['network_path']}")
        if j["url"]:
            lines.append(f"   [View →]({j['url']})")
        lines.append("")
    lines.append("_Reply with job number to draft outreach._")
    lines.append("_Reply \"drafts\" to see all 5 outreach messages._")
    return "\n".join(lines)

def format_followups_and_interviews(followups, interviews, unactioned):
    """Build the CRM section appended to the daily brief."""
    lines = []

    if interviews:
        lines.append("\n📅 *Interviews*")
        for iv in sorted(interviews, key=lambda x: x["days_away"]):
            if iv["days_away"] == 0:
                when = "today"
            elif iv["days_away"] == 1:
                when = "tomorrow"
            elif iv["days_away"] < 0:
                when = f"{abs(iv['days_away'])}d ago"
            else:
                when = f"in {iv['days_away']}d"
            lines.append(f"  • *{iv['company']}* — {iv['role']} ({iv['stage']}) — _{when}_")
            if iv["notes"]:
                lines.append(f"    _{iv['notes']}_")

    if followups:
        lines.append("\n🔔 *Follow-ups Overdue*")
        for f in followups:
            lines.append(f"  • *{f['name']}* @ {f['company']} — sent {f['sent']} ({f['days_ago']}d ago)")

    if unactioned:
        lines.append("\n📥 *Not Yet Actioned*")
        for j in unactioned:
            lines.append(f"  • *{j['role']}* @ {j['company']}" + (f" (score {j['score']})" if j['score'] else ""))

    if not interviews and not followups and not unactioned:
        lines.append("\n✅ *CRM:* Nothing urgent today.")

    return "\n".join(lines)

# ── Main ──────────────────────────────────────────────────────────────────────

def load_seen_jobs():
    """Load cache of previously seen job keys (ordered list, oldest first)."""
    path = os.path.join(WORKSPACE, "seen-jobs.json")
    if not os.path.exists(path):
        return []
    with open(path) as f:
        data = json.load(f)
    # Support legacy set format (unordered)
    if isinstance(data, list):
        return data
    return list(data)


def save_seen_jobs(seen_list):
    """Save seen jobs cache. Evicts oldest entries first (FIFO) at 500 cap."""
    path = os.path.join(WORKSPACE, "seen-jobs.json")
    # Trim from the front (oldest) to keep the most recent 500
    trimmed = seen_list[-500:] if len(seen_list) > 500 else seen_list
    with open(path, "w") as f:
        json.dump(trimmed, f)


def main():
    print(f"[{datetime.now().isoformat()}] Sterl job discovery starting")

    print("Loading network...")
    network = load_network()
    print(f"  {len(network)} companies indexed")

    client = ApifyClient(APIFY_TOKEN)

    start_urls = [
        {"url": f"https://www.linkedin.com/jobs/search/?keywords={urllib.parse.quote(t)}&location=United%20States&f_TPR=r259200"}
        for t in TITLES
    ]

    run_input = {
        "startUrls": start_urls,
        "maxItems": 50,
        "scrapeCompany": True,
        "scrapeJobDetails": True,
    }

    print(f"▶ Running actor via apify-client (.call)...")
    run = client.actor("openclaw/linkedin-jobs-scraper").call(run_input=run_input)

    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    print(f"  {len(items)} raw items from Apify")

    if not items:
        msg = "⚠️ Job discovery: Apify returned 0 results."
        print(msg, file=sys.stderr)
        send_telegram(msg)
        return 1

    # Filter out previously seen jobs before scoring
    seen_list = load_seen_jobs()
    seen_set   = set(seen_list)  # for O(1) lookup
    new_items  = []
    for item in items:
        title   = (item.get("title") or "").lower().strip()
        company = (item.get("companyName") or "").lower().strip()
        key = f"{title}|{company}"
        if key not in seen_set:
            new_items.append(item)
    print(f"  {len(new_items)} new (unseen) items after cache filter")

    # Append new keys to end of list (FIFO — oldest at front, newest at back)
    for item in items:
        title   = (item.get("title") or "").lower().strip()
        company = (item.get("companyName") or "").lower().strip()
        key = f"{title}|{company}"
        if key not in seen_set:
            seen_list.append(key)
            seen_set.add(key)
    save_seen_jobs(seen_list)

    scored = process(new_items if new_items else items, network)
    top5 = scored[:5]

    print("\n🎯 Top 5:")
    for i, j in enumerate(top5, 1):
        print(f"  {i}. {j['title']} @ {j['company']} [{j['location']}] — {j['priority_score']}")
        if j["network_path"]:
            print(f"     🔗 {j['network_path']}")

    out = {
        "timestamp": datetime.now().isoformat(),
        "total_scraped": len(items),
        "total_filtered": len(scored),
        "top_5": top5,
        "all_scored": scored[:20],
    }
    out_path = os.path.join(WORKSPACE, "jobs-today.json")
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"✅ Saved to {out_path}")

    print("Fetching CRM data...")
    followups = get_followups()
    interviews = get_upcoming_interviews()
    unactioned = get_unactioned_jobs()
    print(f"  {len(interviews)} upcoming interviews, {len(followups)} follow-ups due, {len(unactioned)} unactioned jobs")

    brief = format_brief(top5, len(items), len(scored))
    crm = format_followups_and_interviews(followups, interviews, unactioned)

    # Friday pipeline health check
    friday_q = ""
    if datetime.now(timezone.utc).weekday() == 4:  # Friday
        friday_q = "\n\n📊 *Is the pipeline moving? Yes or no.*"
        weekly_count = get_weekly_outreach_count()
        if weekly_count < 5:
            friday_q += f"\n⚠️ Only {weekly_count} outreach sent this week (target: 5). What's blocking?"
        else:
            friday_q += f"\n✅ {weekly_count} outreach sent this week — on track."

    send_telegram(brief + crm + friday_q)
    print("✅ Telegram brief sent")
    return 0

if __name__ == "__main__":
    sys.exit(main())
