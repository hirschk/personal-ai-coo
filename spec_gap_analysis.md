# Sterl OS — Spec Gap Analysis
Last updated: 2026-04-07 (autonomous session)

Reference specs:
- `sterl_os_spec_v1_1.md` (OS-level spec)
- `sterl_job_agent_spec_v2.md` (Job agent spec)

---

## 1. What's in the spec but NOT yet built

### Job Search Agent

| Item | Spec Reference | Gap Severity |
|---|---|---|
| **Follow-up engine — Gmail reply detection** | OS spec §5, Job agent §7 Module 7 | ✅ Built this session |
| **Follow-up timing rules** (Day 0/3/6/10 cadence, draft follow-ups for Hirsch to approve) | Job agent §7 Module 7 | Not built — only auto-detection is live |
| **LinkedIn outreach tracking** (Sterl asks by name each morning, 5:30pm same-day follow-up if not sent) | Job agent §7 Module 7 | Not built — sheet is manual |
| **Outreach templates** (3 message types: direct, intro ask, connection request) | Job agent §7 Module 5 | ✅ Built this session |
| **Afternoon same-day follow-up (5:30pm)** if outreach not sent by midday | OS spec §5, Job agent §7 Module 7 | Not built |
| **MATON_API_KEY / LinkedIn Job Library** | MEMORY.md To Do | Not started |
| **Role-type filter** (exclude non-PM titles from Jobs sheet) | MEMORY.md To Do | Not built |
| **GitHub repo** (README, architecture diagram, sample outputs, SKILL.md files) | Job agent §10 | Not started |

### LinkedIn Content Agent (Domain 2) — **entirely unbuilt**

| Item | Spec Reference | Gap Severity |
|---|---|---|
| **LinkedIn poster skill** (official API, not cookie-based) | OS spec §6, job agent Day 2 | Not installed |
| **Mon/Wed/Fri 6pm content prompt** | OS spec §6 | Not built — evening cron is job-search only |
| **Brain dump → post draft flow** | OS spec §6 Steps 1-4 | Not built |
| **Voice learning loop** (Hirsch edits post → Sterl writes delta to MEMORY.md) | OS spec §6, §5 learning loop | Not built |
| **Cross-domain content mining** (check today's memory before prompting) | OS spec §6 | Not built |
| **Post approval gate** (good/redraft/skip) | OS spec §6 Step 4 | Not built |

### Ideas OS (Domain 3) — **entirely unbuilt**

| Item | Spec Reference | Gap Severity |
|---|---|---|
| **Idea capture flow** (always-on, any message) | OS spec §7 | Not built |
| **Idea structuring prompt** (evening only, structured format) | OS spec §7 | Not built |
| **Ideas tab in Google Sheets** | OS spec §9 Tab 5 | Not created |
| **Saturday 6pm weekly check-in** (wins + active projects + parked ideas) | OS spec §7, §8 | Not built |
| **Non-response escalation** (Sunday silence, Monday morning single question) | OS spec §7 | Not built |
| **Idea activation cron** (breaks into next actions, assigns dates) | OS spec §7 | Not built |

### Cron Schedule Gaps

| Scheduled | Spec Says | Actual |
|---|---|---|
| 9am daily job brief | OS spec §5, §8 | 11am Mon/Wed/Fri only |
| 5:30pm same-day follow-up | OS spec §5, job agent §7 | Not running |
| Saturday 6pm weekly check-in | OS spec §8 | Not running |
| Friday 5:45pm weekly project check-in | OS spec §7 | Not running |
| Sunday = complete silence | OS spec §8 | Not enforced |

### Google Sheets Gaps

| Tab | Spec Says | Actual |
|---|---|---|
| Ideas tab | OS spec §9 Tab 5 | Not created |
| KPIs tab (live weekly metrics) | OS spec §9 Tab 6 | Created but not auto-populated |

---

## 2. What's built but NOT in the spec

| Built | Notes |
|---|---|
| **`job-discovery-apify.py`** — Apify-based LinkedIn scraper | Spec mentioned Apify as a source but didn't define implementation details |
| **`cron-job-discovery.sh`** — wrapper shell script for cron | Spec didn't specify shell wrapper approach |
| **`evening-nudge.py`** — unactioned jobs + overdue outreach check at 6pm | Spec had a "check in if something to do" concept but didn't define this specific script |
| **`interview-followup.py`** — 2pm daily interview reminder | Spec mentioned interview protocol in OS spec §3 (Operating Rules) but didn't spec a dedicated cron |
| **`rebuild-tracker.py` / `fix-jobs-sheet.py`** — one-time setup scripts | Not in spec (setup tooling) |
| **network.md** — 4,261 connections, 3,708 companies indexed | Spec described the data model but not the format |
| **Confidential Jobs blocklist** | Learned from real data, not in spec |
| **Fuzzy match threshold at 0.80** | Spec mentioned fuzzy matching but not the threshold parameter |
| **`gog` CLI** (v0.12.0) as Google auth path | Spec said "connect Google Workspace skill" but didn't specify implementation |
| **Haiku ban** (Sonnet only) | Not in spec — learned from cost/reliability issues |

---

## 3. What to prioritize next (ranked)

### P0 — Completes the job search agent core loop

**1. Day 3/6/10 follow-up drafts (LinkedIn + email)**
The biggest gap between spec and reality. Right now Sterl detects Gmail replies but doesn't draft follow-ups or proactively ask Hirsch whether he sent the LinkedIn messages. The carry-forward logic (never drop unsent outreach) is completely manual. Build:
- Check Outreach sheet for rows with `Status=Sent` and `FollowUp` date passed
- Draft follow-up message, surface to Hirsch for approval
- This is the highest-leverage job search loop tightener

**2. Morning brief — shift to daily 9am (not 3x/week 11am)**
Spec says 9am daily. Current is Mon/Wed/Fri at 11am. Missing Tue/Thu follow-up is a gap. Straightforward cron change + verify the brief script runs daily without issue.

**3. Role-type filter on Jobs sheet**
Currently pulling marketing/non-PM titles. Quick fix to `job-discovery-apify.py` keyword filter. Easy win.

**4. Same-day afternoon nudge (5:30pm)**
If outreach was recommended in the morning brief and Hirsch hasn't replied with status by midday, send a single follow-up. Spec says this should happen same day, not next morning.

---

### P1 — LinkedIn Content Agent (Domain 2)

**5. LinkedIn poster skill via MATON API**
The whole content agent is unbuilt. Before any automation, need:
- MATON_API_KEY from Hirsch
- Install linkedin-api skill from ClawHub
- Test post-to-LinkedIn flow

**6. Mon/Wed/Fri 6pm content prompt**
Once API is connected: update `evening-nudge.py` (or a new `content-prompt.py`) to send the brain dump prompt on content days. Hirsch replies → Sterl drafts → Hirsch approves → posts manually.

**7. Voice learning loop**
When Hirsch edits a draft, he pastes it back. Sterl diffs and writes a voice rule to MEMORY.md. Simple but compounds fast. Build this before automating anything.

---

### P2 — Ideas OS (Domain 3)

**8. Ideas tab in Google Sheets**
Add the Ideas tab. Columns: Idea | Status | First Step | Due Date | Last Update | Notes. One-time setup, 15 minutes.

**9. Saturday weekly check-in cron**
Wins summary + active projects + parked ideas. Can reuse the KPI data already tracked. Hirsch needs this to feel momentum — spec says it's motivating.

**10. Idea capture flow**
Low effort: any message Hirsch sends starting with "idea:" or "sterl, idea:" gets parsed and logged. No structuring prompt yet — just capture first.

---

### P3 — Infrastructure / Polish

**11. GitHub repo**
Spec §10 lists this as a deliverable. Value: interview story, portfolio, replaceability if droplet fails. Needs: README, architecture diagram, anonymized sample outputs.

**12. KPI auto-population**
KPIs tab exists but is static. Auto-populate weekly: outreach sent, replies, interviews booked, posts published. Useful for the Saturday brief.

**13. Sunday silence enforcement**
Technically requires a guard in every cron script that checks `datetime.weekday() != 6`. Low effort, spec says "no exceptions."

---

## Summary Table

| Priority | Item | Effort | Impact |
|---|---|---|---|
| P0-1 | Follow-up draft engine (Day 3/6/10) | Medium | Very High |
| P0-2 | Shift to 9am daily brief | Low | High |
| P0-3 | Role-type filter | Low | Medium |
| P0-4 | Same-day 5:30pm nudge | Low | Medium |
| P1-5 | MATON_API_KEY + LinkedIn skill | Low (auth) | Unlocks Domain 2 |
| P1-6 | Mon/Wed/Fri content prompt | Medium | High |
| P1-7 | Voice learning loop | Low | High (compounds) |
| P2-8 | Ideas tab in Sheets | Low | Medium |
| P2-9 | Saturday weekly check-in | Medium | High |
| P2-10 | Idea capture flow | Low | Medium |
| P3-11 | GitHub repo | Medium | Medium (interview story) |
| P3-12 | KPI auto-population | Medium | Medium |
| P3-13 | Sunday silence guards | Low | Low |
