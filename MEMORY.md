# MEMORY.md — Sterl Long-Term Memory

Last updated: 2026-04-10

---

## Who I Am

Sterl — Hirsch's external prefrontal cortex and COO. Running on OpenClaw, DigitalOcean NYC1 (67.205.179.96). Telegram only.

---

## Who Hirsch Is

- **Name:** Hirsch Keshav — Senior AI PM, full-stack AI builder
- **Telegram ID:** 8768439197
- **Target roles:** Head of Product, VP Product, Director of Product
- **Target industries:** Fintech, AI-native, AI-forward
- **Timezone:** UTC-5 year-round (Playa del Carmen, Quintana Roo — no DST, permanently UTC-5)
- **Energy:** High 8am-12pm, low 12-4pm, second wind 6-10pm
- **GitHub:** github.com/hirschk/personal-ai-coo

---

## Repo Config

- **Remote:** `git@github.com:hirschk/personal-ai-coo.git`
- **Auth:** SSH deploy key `/root/.ssh/sterl_github` — permanent, no expiry
- **Workspace:** `/root/.openclaw/workspace/`
- **Push:** `git add . && git commit -m "msg" && git push origin main`

---

## Tasks & Projects

Tasks and Projects live in Google Sheets (Sheet ID: `1o6XXLhpxFVZL5SlDKP8a56Y17brgmD7HWzAGe1Ei4Co`).
- **Projects tab** = active/parked/done projects (formerly "Ideas")
- **Tasks tab** = individual actions. Columns: `Task ID | Name | Project ID | Status (todo/in-progress/done/parked) | Due Date | Notes`
- `Project ID` is nullable — blank = free-floating task
- Source of truth is always Sheets. Never cache task state in memory. Only load when asked.

---

## Infrastructure

- **Model:** Claude Sonnet. Haiku for cron scripts (ideas-structure, linkedin-draft, voice-update).
- **Prompt caching:** ON (`cacheRetention: long`)
- **maxTokens:** 1500
- **Heartbeats:** OFF
- **Google OAuth:** Sheets (write) + Gmail (readonly) + Calendar (readonly)
- **Apify token:** in `/root/.openclaw/workspace/.env` and `/etc/environment`
- **Sheet ID:** `1o6XXLhpxFVZL5SlDKP8a56Y17brgmD7HWzAGe1Ei4Co`

---

## Active Pipeline (as of 2026-04-08)

### Interviews
| Company | Role | Stage | Notes |
|---|---|---|---|
| Ramp | Product Manager | Recruiter Screen | Done Apr 8. Thank-you sent to Yeno. |
| Phoenix Technologies | Senior PM | CPO Round 2 | Done Apr 8. Thank-you sent to Timothy Schulz. Demoed Sterl. |
| Defense SaaS (James) | VP Product | Shortlisting | Via James Winters. **DO NOT mention Claude/OpenClaw.** 1099, tax treaty TBD. |
| Katalyze AI | Head of Product | Passed | Comp mismatch — under $250K |

### Outreach Awaiting Reply
| Name | Company | Sent | Days |
|---|---|---|---|
| James Chiu | Cedar | Apr 7 | 1 |
| Matas Sriubiskis | Instacart | Apr 7 | 1 |
| Jason Finkelstein | Amex | Apr 8 | D7 follow-up sent. Next: Apr 15 |
| Monica Rincon | JP Morgan | Apr 8 | D7 follow-up sent. Next: Apr 15 |
| Austin Osborne | JP Morgan | Apr 8 | D7 follow-up sent. Next: Apr 15 |
| Tejas Savalia | JP Morgan | Apr 8 | D7 follow-up sent. Next: Apr 15 |

### Unactioned / Pending
- Plaid (Ali Vira — PM), Chime (Shreya Sudarshana — Sr PM), Navan (Alia Kaussar — Sr PM) — warm connections, draft Expandi-style outreach leading with Ramp interview
- Monzo x2 — parked (no connection)

---

## Key Contacts

- Jason Li — Design Director @ Ramp — referred resume
- James Chiu — Director, Product Design @ Cedar
- James Winters — Recruiter, Defense SaaS
- Matas Sriubiskis — Senior PM @ Instacart
- Yeno — Recruiter @ Ramp
- Timothy Schulz — CPO @ Phoenix Technologies

---

## Outreach Message Flow (LinkedIn Network)

When running batch outreach from a CSV or list:
1. Show all 5 company/person/role combos in **one message** upfront
2. Then feed DM messages **one at a time** — wait for approval/edits before next
3. Flag duplicates (same contact, different company) and irrelevant companies
4. Skip contacts already in the active pipeline unless Hirsch says otherwise

---

## Operating Rules

1. **Carry-Forward:** never drop anything unless Hirsch says pass/done/park
2. **Interview Follow-Up:** thank-you within 2h of interview, re-fire at 24h if not confirmed
3. **Friday:** "Is the pipeline moving? Yes or no."
4. **Memory standup:** read MEMORY.md at session start, write summary at session end
5. **Acknowledge immediately** for any task >30 seconds, confirm when done

---

## LinkedIn Voice Rules

- Short sentences. No em dashes. No filler openers.
- No "excited to share". No corporate buzzwords.
- PM-native: "shipped", "mapped to outcomes", "found in the data"
- Understated. Real question at end, not rhetorical.
- **Post footer (always):** "Open to my next role. Head of Product or Senior PM, AI-native companies. NYC, LA, Miami, Austin, or remote. Hit me if AI is core to what you're building."

---

## KPIs (baseline Mar 26 — Apr 8)

- Messages sent: 11 | LinkedIn posts: 5 | Interviews: 3 | Active pipeline: 3

---

## Lessons Learned (2026-04-10)

- **UTC-5 always** — Playa del Carmen / Quintana Roo does not observe DST. Never assume EDT (UTC-4). Always UTC-5.
- **Jobs status lifecycle:** `new → outreaching → applied → screening → interviewing`. "Outreaching" = messaged a connection, waiting for confirmation. Never mark "applied" until referral is confirmed.
- **Telegram Markdown breaks on parens/slashes** — switch to HTML parse mode for all dynamic content. Use `<b>` not `*bold*`.
- **Contacts in conversation ≠ contacts in sheet** — if it's not in the Jobs tab, the morning brief can't see it. Always load CSVs into the sheet immediately.
- **Paused jobs should be skipped** — same as removed. Add to SKIP_JOB_STATUSES.
- **Undated tasks are invisible by default** — script must surface them separately or they fall through forever.
- **Section numbering** — render sections dynamically so numbering is always sequential regardless of which are empty.
- **Two nudges daily** — 12:30pm and 9:45pm EST (17:30 and 02:45 UTC). Hirsch does /new twice a day to reset context.

## Known Issues

- [ ] Cron fires 16:00 UTC = 12pm EDT (not 11am) — adjust to 15:00 UTC if needed
- [ ] Sunday silence not implemented
- [ ] Anthropic key not in .env (needed for linkedin-draft.py subprocess)

## Last Run
Last job brief: 2026-04-08 — 38 scraped, 13 matched

## Last Run
Last session-close: 2026-04-10 — 0 commits, 1 crons ran, 2 active interviews

### What was built
- **Tasks tab** created in Google Sheets: `Task ID | Name | Project ID | Status | Due Date | Notes` — 6 tasks loaded (T001–T006)
- **Projects tab** renamed from Ideas, migrated to schema: `Project ID | Name | Status | Due Date | Notes` — P001 Fintech outreach, P002 LinkedIn Expandi funnel
- **followup-sequence.py** extended: reads Tasks tab, sends tasks due today/overdue as morning brief section
- **friday-checkin.py** rebuilt cleanly: active projects + incomplete task counts + overdue solo tasks
- **SOUL.md** updated: "proactive" redefined as removing friction (deliver drafts, never just remind)
- Committed `fe006bb` — scripts/followup-sequence.py + scripts/friday-checkin.py
- Idle reset bumped from 2h → 6h in openclaw.json

### Outreach sent today (Apr 9)
| Name | Company | Notes |
|---|---|---|
| Ali Vira | Plaid | Staff PM AI Foundations. Resume attached. |
| Shreya Sudarshana | Chime | Group PM Platform role. |
| Alia Kaussar | Navan | AI financial automation angle. |

### Pipeline update
- **Ramp**: Advanced to Hiring Manager round. Interview Apr 10 12:00–12:30pm EST with William Simmons (Dir, Financial Efficiency & Intelligence)
- **Phoenix Technologies**: CPO round 2 done Apr 8. Thank-you sent. Awaiting next step.
- **Defense SaaS (James Winters)**: Shortlisting. DO NOT mention Claude/OpenClaw.

### Follow-up schedule
- Apr 12: James Chiu (Cedar) D7, Matas Sriubiskis (Instacart) D7 — D3 fired Apr 10, sheet advanced
- Apr 12: Ali Vira (Plaid), Shreya Sudarshana (Chime), Alia Kaussar (Navan) D3
- Apr 15: JP Morgan x3 + Amex D14

---

## Session Log: 2026-04-10

### Pipeline
- **Ramp**: Hiring Manager interview today 12:00–12:30pm EST w/ William Simmons (Dir, Financial Efficiency & Intelligence)
- **Phoenix Technologies**: Awaiting next step after CPO round 2 (Apr 8)
- **Defense SaaS (James Winters)**: Shortlisting. DO NOT mention Claude/OpenClaw.

### Uncontacted leads (surfaced by morning brief)
- Basel Hegazi @ Confidential Jobs — Director of Product Management (AI)
- Pabi Ambikainathan @ Iterable — Senior PM
- Both appear in Section 2 (First contacts) every morning until actioned

### What was built
- **followup-sequence.py fully redesigned** — commit `0709808`
  - Now sends 4-section morning brief daily (never silent unless everything empty)
  - Section 1: Follow-ups due (D3/D7/D14) — stage normalized, handles "D14 (Apr 15)" format
  - Section 2: First contacts not yet sent — Jobs w/ Network Path not in Outreach (carry-forward)
  - Section 3: New contacts for today — up to 5 Jobs by Priority Score
  - Section 4: Tasks due/overdue
  - Root cause of missed D3s fixed: blank col-G rows now handled gracefully
  - Bot token typo fixed: `_0xyFz3` → `_0xyF3`
- Cron confirmed correct: 13:30 UTC = 9:30am EDT daily
