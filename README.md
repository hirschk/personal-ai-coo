# sterl-job-search-agent
An autonomous job search agent built on OpenClaw. Scans LinkedIn jobs every 48hrs, maps them to my network, drafts personalized outreach by name, follows up automatically, and delivers everything via Telegram
# Sterl — Personal AI Chief Operating Officer

> Built by a non-technical PM with zero coding background. No engineers. No budget. One afternoon.

**Sterl OS v0.1**

```
✅ Core infrastructure live
✅ Candidate profile + network indexed  
✅ Job scoring logic defined
⏳ Job discovery engine (in progress)
⏳ Autonomous outreach (draft-first, human-approve)
⏳ Ideas OS (planned)

Deployment: DigitalOcean NYC1 + Telegram
Model: Claude Haiku (chat) / Claude Sonnet (heavy tasks)
Network: 4,261 connections across 3,708 companies
```

---

## What it does

Sterl is a personal AI agent that runs 24/7 on a cloud server and works your job search automatically.

Every 48 hours it scans new job postings, figures out who you know at those companies, writes a personalized outreach message for each person, and delivers everything to your phone via Telegram.

If you haven't sent the messages by afternoon, it follows up. By name.

*"Did you send that note to Sarah at Cursor?"*

The only number it tracks is **interviews per week**.

---

## How it works

```
LinkedIn Jobs (Apify) → Job Scoring Engine → Network Matching (LinkedIn CSV)
→ Outreach Drafts → Telegram Daily Brief → Google Sheets Tracker
```

**Job discovery:** Scans LinkedIn jobs posted in the last 48 hours filtered by target titles and locations. Scores each job by role fit, network access, and recency.

**Network matching:** Maps job companies against your LinkedIn connections export. Ranks connections by relevance — product roles first, recruiting second, any connection third.

**Outreach generation:** Drafts three message types per opportunity — direct outreach, intro requests, and connection requests — in your voice.

**Follow-up cadence:** Day 3 → Follow-up #1. Day 6 → Follow-up #2. Day 10 → Final touch. Then cold. Always draft-first, never auto-sends.

**Daily brief:** Every weekday at 11am via Telegram — top 5 opportunities, best contact, exact message, why it's prioritized.

**Weekly check-in:** Every Friday — interviews booked, outreach sent, conversations active, pipeline velocity warning if outreach is low.

---

## Tech stack

| Component | Tool |
|---|---|
| Agent runtime | [OpenClaw](https://openclaw.ai) |
| LLM | Claude Sonnet 4.6 (heavy tasks) + Haiku (routine) |
| Interface | Telegram |
| Hosting | DigitalOcean Droplet ($6/month) |
| Job scraping | Apify LinkedIn Jobs Scraper (MCP) |
| Network data | LinkedIn Connections CSV export |
| Tracker | Google Sheets |
| Memory | OpenClaw MEMORY.md (markdown-based persistence) |

---

## Scoring logic

```
priority_score =
  (0.4 × fit_score)
+ (0.4 × network_score)
+ (0.2 × recency_score)
```

**fit_score** — role title, seniority, industry match against candidate profile

**network_score** — 1st degree connection in product role = 1.0, recruiting = 0.7, any role = 0.5, no connection = 0.0

**recency_score** — posted <48hrs = 1.0, 2-4 days = 0.7, 5-7 days = 0.3, >7 days = 0.0

---

## Daily Telegram brief format

```
Morning. Here's your job search brief.

FOLLOW-UPS
Gmail: Waiting on Bob Chen (Stripe, emailed Apr 1).
LinkedIn: Did you send the messages to Sam at Cursor, 
Joe at Ramp, and Sally at Brex?

TODAY'S TOP 5
1. Head of Product @ Cursor (9.2) — You know Sarah Lee. Draft ready.
2. VP Product @ Rippling (8.7) — You know Mike Wang. Draft ready.
3. Director of Product @ Plaid (7.9) — No connection. Request drafted.
4. Head of AI Product @ Notion (7.4) — Intro ask drafted.
5. Senior PM @ Linear (6.8) — No connection. Request drafted.

Reply "drafts" to see all 5 messages.
```

---

## Setup

### Prerequisites
- Anthropic API key (console.anthropic.com)
- Telegram account
- DigitalOcean account (or any VPS)
- LinkedIn connections CSV export
- Apify account (for LinkedIn job scraping)
- Google account (for Sheets tracker)

### Install

```bash
# On your VPS
curl -fsSL https://openclaw.ai/install.sh | bash
openclaw onboard
```

### Connect Telegram
1. Message @BotFather on Telegram
2. Run /newbot and get your token
3. Paste token during openclaw onboard
4. Approve pairing: `openclaw pairing approve telegram <code>`

### Feed your data
Send Sterl your resume and LinkedIn CSV via Telegram. It parses both and builds your candidate profile and network map automatically.

### Set cron jobs
```
openclaw cron add --name "job-search-brief" --schedule "0 11 * * 1-5"
openclaw cron add --name "linkedin-content" --schedule "30 17 * * 1,3,5"
openclaw cron add --name "weekly-checkin" --schedule "0 17 * * 5"
```

---

## Architecture

```
[LinkedIn Jobs API] → [Apify MCP Scraper]
                              ↓
[LinkedIn CSV] → [Network Mapper] → [Scoring Engine]
                                          ↓
                              [Outreach Generator]
                                          ↓
                    [OpenClaw Gateway] → [Telegram]
                              ↓
                    [Google Sheets Tracker]
                              ↓
                    [MEMORY.md — persistent state]
```

---

## About

Built by **Hirsch Keshav** — Senior AI Product Manager.

10+ years in AI product. Zero coding background. Accounting degree.

Built this in one afternoon from a cenote in Tulum.

---

*"You generate. Sterl executes."*
