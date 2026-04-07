# Sterl — Network-First Job Search Agent
## Full System Spec v2.0
### Built on OpenClaw | Delivered via Telegram | Powered by Claude Sonnet

---

## 0. One-Line Summary

Sterl identifies the best live roles, finds who Hirsch knows inside those companies, tells him exactly who to message, writes the message, follows up by name every morning, and tracks everything — until interviews happen.

---

## 1. Core Philosophy

This system is not about applying to jobs.

It is about:
**Turning jobs into conversations → conversations into interviews.**

Primary KPI: **Interviews per week**

Leading KPIs:
- Companies networked into per week
- Warm outreach messages sent per week
- Intro requests sent per week
- Active conversations open
- Follow-ups executed on time
- Jobs with viable warm path identified

---

## 2. Architecture Overview

```
INPUTS
├── Resume (PDF/DOCX → parsed once, stored as candidate_profile.md)
├── LinkedIn Connections Export (CSV → parsed once, stored as network.md)
├── Job Preferences (titles, locations, stored as preferences.md)
└── Gmail (read continuously via Gmail skill)

PIPELINE
Ingestion → Normalization → Matching → Ranking → Action Engine → Output

STATE LAYER (OpenClaw MEMORY.md + daily memory files)
├── All recommended outreach logged by name, company, channel, date
├── All sent/pending/replied statuses
├── Carry-forward logic for unsent recommendations
└── Auto-flush to disk before session compaction

OUTPUTS
├── Telegram (daily brief + proactive follow-up questions)
├── Google Sheets (live tracker — Jobs, Contacts, Outreach, Interviews, KPIs)
└── Outreach messages (draft only — Hirsch sends manually)
```

---

## 3. Data Models

### CandidateProfile (candidate_profile.md)
- name, seniority level
- target roles (Head of Product, VP Product, Director of Product)
- industries (fintech, AI-native, AI-forward)
- key outcomes (Deloitte $8M ARR, EF-backed founder, Hearth ARR opportunity)
- skills (AI product, 0→1, data-driven PM, cross-functional leadership)
- voice/tone for outreach (direct, warm, no corporate buzzwords)

### Job
- job_id
- title
- company
- url
- posted_at
- description
- fit_score (0-1)
- network_score (0-1)
- recency_score (0-1)
- priority_score
- status (new / actioned / pass)

### Contact
- name
- company (normalized)
- title
- linkedin_url
- relevance_score (product role = high, recruiting = medium, other = low)
- relationship_strength (1st degree)

### OutreachRecord
- date_recommended
- job_id
- contact_name
- contact_company
- contact_title
- message_type (direct / intro_ask / connection_request)
- message_draft
- channel (linkedin / gmail)
- status (recommended / sent / replied / meeting_booked / no_response)
- follow_up_due_date
- notes

### Interview
- company
- role
- stage
- date
- notes

---

## 4. Scoring Logic

```
priority_score =
 (0.4 × fit_score)
+ (0.4 × network_score)
+ (0.2 × recency_score)
```

**fit_score:** How well the role matches candidate profile (title, seniority, industry)

**network_score:** 
- 1st degree connection at company in product role = 1.0
- 1st degree connection at company in recruiting = 0.7
- 1st degree connection at company in any role = 0.5
- No connection = 0.0

**recency_score:**
- Posted < 48 hours = 1.0
- Posted 2-4 days = 0.7
- Posted 5-7 days = 0.3
- Posted > 7 days = 0.0

---

## 5. Network Matching Design

### CSV Ingestion
LinkedIn connections CSV exported manually by Hirsch and fed to Sterl.

Sterl normalizes company names using fuzzy matching:
- "Google LLC" → "Google"
- "Google DeepMind" → "Google"
- "Meta Platforms" → "Meta"

Sterl flags ambiguous matches for human confirmation on first run.

### Deduplication Rule
Same person appearing under multiple company name variants = one contact record. Sterl merges on LinkedIn URL as the canonical unique identifier.

### Output
Internal map: `Company (normalized) → [list of 1st degree connections with titles]`

Stored as `network.md` in workspace. Updated when Hirsch provides a new CSV export.

---

## 6. State Management

### How Sterl remembers everything

OpenClaw writes state to plain markdown files in the workspace:

**MEMORY.md** — permanent long-term memory
- Candidate profile summary
- Job preferences
- Outreach voice/tone rules
- Key contacts Hirsch has relationships with
- Lessons learned from outreach edits

**memory/YYYY-MM-DD.md** — daily state
- Jobs surfaced today
- Outreach recommended today (by name, company, channel)
- Status updates received from Hirsch
- Follow-ups pending

**Deduplication rule:**
Before recommending any outreach, Sterl checks MEMORY.md and daily files:
*"Has this contact already been messaged? Is there an open thread?"*
If yes → skip and note status instead.

### Session compaction protection
Before any session compaction, OpenClaw automatically flushes critical state to disk. Sterl also writes a daily summary to `memory/YYYY-MM-DD.md` at the end of each cron run so nothing is lost between sessions.

---

## 7. Core Modules

### Module 1: Resume Parser (run once)
- Hirsch pastes resume text or uploads PDF
- Sterl extracts structured CandidateProfile
- Saves to `candidate_profile.md`
- Confirms back: "Here's what I know about you — does this look right?"

### Module 2: Network Ingestion (run once, refresh monthly)
- Hirsch exports LinkedIn connections CSV and feeds to Sterl
- Sterl parses, normalizes company names, deduplicates
- Saves to `network.md`
- Reports: "I've mapped X connections across Y companies"

### Module 3: Job Discovery (runs daily via cron)
- Pulls jobs posted in last **48 hours** (not 7 days)
- Sources: LinkedIn Jobs via Apify MCP scraper
- Filters by: target titles, target locations
- Returns: title, company, URL, description, posted_at
- Scores each job using scoring logic above
- Matches against network.md for network_score

### Module 4: Ranking Engine
- Applies priority_score formula
- Filters out jobs already actioned
- Selects top 5 for daily brief

### Module 5: Outreach Generator
For each of the top 5 jobs, generates:

**A. Direct outreach** (1st degree connection at company)
```
Hey [Name], hope you're well. I saw [Company] is hiring 
a [Role] — I'm currently exploring my next move in AI product 
and [Company]'s work on [specific thing] caught my attention. 
Would love to grab 15 mins if you're open to it. Either way, 
no pressure at all.
— Hirsch
```

**B. Intro request** (connection knows someone at company)
```
Hey [Name], quick one — I noticed you're connected to 
[Target] at [Company]. They're hiring a [Role] and it looks 
like a great fit. Any chance you'd be comfortable making 
an intro? Happy to send a blurb. Thanks either way.
```

**C. Connection request** (no existing connection)
```
Hi [Name] — I'm a Head of Product / AI PM exploring my 
next role. Your work at [Company] on [specific thing] 
caught my eye. Would love to connect.
```

All messages: short, human, specific, no buzzwords, ready to send.

**Learning loop:** When Hirsch edits a draft before sending, he pastes the edited version back to Sterl. Sterl writes the delta to MEMORY.md as a voice rule. Messages improve weekly.

### Module 6: Daily Action Engine (cron — 9am daily)

Telegram message format:
```
Good morning Hirsch. Here's your job search brief for today.

FOLLOW-UPS NEEDED
Gmail: Still waiting on replies from Bob Chen (Stripe, emailed Apr 1) 
and Jim Park (Ramp, emailed Mar 30). No new emails from either.

LinkedIn check-in: Did you send the 3 messages I drafted yesterday?
→ Sam Chen at Stripe
→ Joe Kim at Ramp 
→ Sally Park at Brex
Reply with their status and I'll update the tracker.

TODAY'S TOP 5 OPPORTUNITIES
1. Head of Product @ Cursor (priority: 9.2) — You know Sarah Lee (PM there). Draft ready.
2. VP Product @ Rippling (priority: 8.7) — You know Mike Wang (Engineering). Draft ready.
3. Director of Product @ Plaid (priority: 7.9) — No connection. Connection request drafted.
4. Head of AI Product @ Notion (priority: 7.4) — You know Chris Park (recruiter). Intro ask drafted.
5. Senior PM, AI @ Linear (priority: 6.8) — No connection. Connection request drafted.

Reply "drafts" to see all 5 messages.
Reply "pass [number]" to skip a job.
Reply "done [number]" to mark as actioned.
```

### Module 7: Follow-Up Engine

**Gmail path (autonomous):**
- Sterl reads Gmail daily via Gmail skill
- Detects: replies, intro emails, interview scheduling requests
- Auto-updates OutreachRecord status in Sheets
- Alerts Hirsch via Telegram: *"Bob Chen replied to your email. Looks like he's open to a call — want me to draft a response?"*

**Outreach volume rule:**
If fewer than 5 outreach messages sent in a week, flag it in the Friday brief with Hirsch's current job search runway and a specific recommendation on what to reprioritize to hit the number.

**LinkedIn path (human-in-loop):**
- Sterl asks proactively by name every morning (11am brief)
- If messages are still unsent by the afternoon check-in (5:30pm), Sterl follows up same day — not next morning
- Hirsch reports status in Telegram reply
- Sterl writes to MEMORY.md and Sheets tracker
- Only truly unactioned items carry forward to next day's brief

**Follow-up timing rules (applies to both Gmail and LinkedIn):**
- Day 0: Message sent
- Day 3 no reply → Sterl drafts follow-up #1, surfaces to Hirsch for review before sending
- Day 6 no reply → Sterl drafts follow-up #2, surfaces to Hirsch for review before sending
- Day 10 no reply → Sterl drafts final touch, surfaces to Hirsch for review before sending
- After final touch with no reply → mark cold, stop following up
- Reply received at any stage → Sterl drafts next step message within the hour

**Rule: Sterl never auto-sends follow-ups. Every draft is surfaced to Hirsch first.**

### Module 8: Gmail Integration
- Read inbox for replies to outreach
- Detect interview scheduling emails
- Detect intro emails forwarded to Hirsch
- Update Sheets tracker automatically
- Alert Hirsch for anything requiring action

### Module 9: Google Sheets Tracker

**Tab 1: Jobs**
| Company | Role | URL | Priority Score | Network Path | Status | Date Added |

**Tab 2: Contacts**
| Name | Company | Title | LinkedIn URL | Relevance Score | Connection Status |

**Tab 3: Outreach**
| Date | Name | Company | Channel | Message Type | Status | Follow-Up Date | Notes |

**Tab 4: Interviews**
| Company | Role | Stage | Date | Notes |

**Tab 5: KPI Dashboard**
| Week | Interviews | Companies Networked | Outreach Sent | Intros Requested | Active Conversations |

---

## 8. Build Plan

### Day 1 — Foundation
- [ ] Feed resume to Sterl → generate candidate_profile.md
- [ ] Export LinkedIn CSV → feed to Sterl → generate network.md
- [ ] Set job preferences (titles, locations) → preferences.md
- [ ] Verify network matching: "Who do I know at Stripe?" test
- [ ] Create Google Sheets tracker with all 5 tabs
- [ ] Connect Google Workspace skill (OAuth)
- [ ] Connect Gmail skill

### Day 2 — Job Engine + Matching
- [ ] Install Apify LinkedIn Jobs scraper via MCP
- [ ] Build scoring logic as custom SKILL.md
- [ ] Test: run job discovery manually, verify top 5 output
- [ ] Build outreach templates for all 3 message types
- [ ] Test full pipeline: job → match → score → draft message
- [ ] Install LinkedIn poster skill (official API, not cookie-based)

### Day 3 — Automation + Delivery
- [ ] Connect Telegram (BotFather → token → openclaw channels login)
- [ ] Set daily 9am cron job
- [ ] Test full daily brief end-to-end via Telegram
- [ ] Test follow-up flow: Sterl asks by name, Hirsch replies, Sheets updates
- [ ] Set session memory rules (MEMORY.md auto-flush)
- [ ] First live daily brief hits phone ✅

---

## 9. Security Notes

- All outreach is **draft only** — Hirsch sends manually. No autonomous sending.
- LinkedIn messages sent manually by Hirsch — no scraping, no automation detection risk
- Gmail read-only for detection — Sterl drafts replies, Hirsch sends
- Only verified ClawHub skills installed — check VirusTotal scan before any install
- Anti-loop rule in every cron: *"If a task fails twice, stop and alert Hirsch via Telegram"*

---

## 10. GitHub Deliverables

- [ ] README with system overview and architecture
- [ ] Architecture diagram (Mermaid)
- [ ] Sample daily brief output (anonymized)
- [ ] Sample outreach messages (anonymized)
- [ ] Tracker schema / screenshot
- [ ] SKILL.md files for custom skills built
- [ ] Setup instructions (for demo purposes)

---

## 11. Interview Story

*"I was job searching for a Head of Product role. Instead of cold applying, I built a personal AI agent on OpenClaw that reads live job postings, maps them to my LinkedIn network, drafts warm outreach by name, follows up proactively every morning, and tracks my entire pipeline in Google Sheets. I got my first interview from a warm intro it surfaced in week one. Here's the GitHub repo."*

---

*Spec v2.0 — Hirsch + Claude — April 2026*
*Build starts: Day 1 after Telegram live + API funded*
