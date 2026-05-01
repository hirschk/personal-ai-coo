# MEMORY.md — Sterl Long-Term Memory

Last updated: 2026-04-10

---

## Who I Am

Sterl — Hirsch's external prefrontal cortex and COO. Running on OpenClaw, DigitalOcean NYC1 (67.205.179.96). Telegram only.

---

## Who Hirsch Is

- **Name:** Hirsch Keshav — Senior AI PM, full-stack AI builder
- **Telegram ID:** 8768439197
- **Title:** Senior PM (most recently at Hearth, Series B fintech — NOT Head of Product)
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

## Google Sheets (Source of Truth)

Sheet ID: `1o6XXLhpxFVZL5SlDKP8a56Y17brgmD7HWzAGe1Ei4Co`

Tabs:
- **Interviews** — active interview pipeline
- **Outreach** — all DMs/emails sent, follow-up dates
- **Jobs** — scraped job listings, status, priority
- **Contacts** — key people, companies, notes
- **KPIs** — weekly metrics
- **Projects** — active/parked/done projects
- **Tasks** — individual actions (`Task ID | Name | Project ID | Status | Due Date | Notes`)

Never cache pipeline state in MEMORY.md. Always load from Sheets when asked.

---

## Infrastructure

- **Model:** Claude Sonnet. Haiku for cron scripts.
- **Prompt caching:** ON (`cacheRetention: long`)
- **maxTokens:** 1500
- **Heartbeats:** OFF
- **Google OAuth:** Gmail (readonly) + Calendar (readonly) — gog CLI only for Gmail/Calendar
- **Sheets:** Service account ONLY — `config/sterl-sheets-key.json`. Never use `gog sheets` commands. gog OAuth is expired and not maintained.
- **Apify token:** in `/root/.openclaw/workspace/.env` and `/etc/environment`

---

## Job Search Strategy (updated Apr 14, 2026)

Two tracks — not compromising on both simultaneously:

**Track A: Toronto in-person**
- Series C+ or big recognized brand (Amex, Deloitte, Shopify, Stripe, Google, etc.)
- Must be a name that means something — no Series A or under
- Goal: big office, fun culture, more chill, brand equity on resume
- Back in Toronto for the summer

**Track B: Remote US role**
- Live in Toronto, US-paying salary
- Target: $180–200K USD (already ~30% more than Canadian equivalent)
- Contract preferred — tax savings on top of currency arbitrage
- Company location doesn't matter as long as it's fully remote

Rule: if it's in-person → must be big brand. If it's remote → must pay US rates.

---

## Where to Look Things Up

- **Pipeline / interviews / stages** → Interviews tab
- **Outreach / follow-up dates / who was contacted** → Outreach tab
- **Job listings / company status** → Jobs tab
- **People / relationships / notes on contacts** → Contacts tab
- **Weekly metrics** → KPIs tab
- **Projects** → Projects tab
- **Tasks / to-dos** → Tasks tab

When Hirsch asks anything about people, pipeline, outreach, or tasks — fetch from Sheets first. Don't guess from memory.

---

## Operating Rules

1. **Check before asking:** Always check the sheet (or relevant source) before asking Hirsch about status. Never ask him something you could look up yourself.
2. **Carry-Forward:** never drop anything unless Hirsch says pass/done/park
2. **Interview Follow-Up:** thank-you within 2h of interview, re-fire at 24h if not confirmed
3. **Friday:** "Is the pipeline moving? Yes or no."
4. **Memory standup:** read MEMORY.md at session start, write summary at session end
5. **Acknowledge immediately** for any task >30 seconds, confirm when done
6. **Defense SaaS (James Winters):** DO NOT mention Claude or OpenClaw. Ever.
7. **"Locked in" = sheet updated**, not just MEMORY.md

---

## Outreach Message Flow (LinkedIn Network)

When running batch outreach from a CSV or list:
1. Show all 5 company/person/role combos in **one message** upfront
2. Then feed DM messages **one at a time** — wait for approval/edits before next
3. Flag duplicates (same contact, different company) and irrelevant companies
4. Skip contacts already in the active pipeline unless Hirsch says otherwise

---

## LinkedIn Voice Rules

- Short sentences. No em dashes. No filler openers.
- No "excited to share". No corporate buzzwords.
- PM-native: "shipped", "mapped to outcomes", "found in the data"
- Understated. Real question at end, not rhetorical.
- **Post footer (always):** "Open to my next role. Head of Product or Senior PM, AI-native companies. NYC, LA, Miami, Austin, or remote. Hit me if AI is core to what you're building."

---

## Corrections

- **Hearth title:** Senior PM, not Head of Product. Always use "senior AI PM, most recently at Hearth (Series B fintech)" in outreach.

---

## Lessons Learned

- **UTC-5 always** — Playa del Carmen / Quintana Roo does not observe DST. Never assume EDT (UTC-4). Always UTC-5.
- **Jobs status lifecycle:** `new → outreaching → applied → screening → interviewing`. "Outreaching" = messaged a connection. Never mark "applied" until referral confirmed.
- **Telegram Markdown breaks on parens/slashes** — use HTML parse mode for dynamic content. `<b>` not `*bold*`.
- **Contacts in conversation ≠ contacts in sheet** — always load CSVs into sheet immediately.
- **Paused jobs should be skipped** — add to SKIP_JOB_STATUSES.
- **Undated tasks are invisible by default** — surface them separately.
- **Section numbering** — render dynamically so numbering is always sequential.
- **Two nudges daily** — 12:30pm and 9:45pm EST (17:30 and 02:45 UTC).

## Session Log: 2026-05-01

### Done
- LinkedIn post published: Telegram bot hijack story ("My AI agent got hijacked") — strong personal/PM-learning angle
- 9 new LinkedIn voice rules saved to voice_rules.md (kill fear first, prose > bullets for incidents, battle scar reframe, warm community close, etc.)
- Brian Jorgenson (CPO, Wolters Kluwer) — asked for resume on LinkedIn — T015 added, logged to Outreach, follow-up May 4, brianj.jorgenson@wolterskluwer.com
- All changes pushed to GitHub

### Pending
- Brian Jorgenson — send resume (T015), follow-up May 4
- Austin recruiter blast — 40 contacts ready, priority 4 first (Somer, Vicente, Allen, Charl)
- Follow-ups May 2: Derek (Demand Inc), Doug (EBM AI), Neeraj (Deloitte Ventures), Pedro (Brex)
- Follow-ups May 4: Tulloch, Skrylev, Razib, recruiter blitz
- VC Talent Partner DMs (5, Austin/LA) — overdue since Apr 15
- Seleena Juma — confirm she shared resume with Wealthsimple + Accenture FS
- LinkedIn profile update (T009) — 3+ weeks in queue
- Austin HM DMs (Visa/Circle/Pismo) — overdue Apr 16

---

## Session Log: 2026-04-30

### Done
- Telegram token rotated (bot was hijacked — name changed to "ШЕРЛОК")
- New token added to `.env` as `TELEGRAM_TOKEN`
- All 12 scripts: hardcoded token replaced with `os.environ.get("TELEGRAM_TOKEN")` + `python-dotenv`
- All 12 scripts: hardcoded `TELEGRAM_CHAT_ID` replaced with `os.environ.get("TELEGRAM_CHAT_ID")`
- `TELEGRAM_CHAT_ID=8768439197` added to `.env`
- `scrape-and-score.py` + `job-discovery.py`: APIFY placeholder removed, uses env var
- `rebuild-tracker.py`, `fix-jobs-sheet.py`, `load-csv-to-jobs.py`, `gmail-reply-check.py` (Sheets client): switched from OAuth to service account
- Old token purged from entire git history via `git filter-repo`, force-pushed
- RUNBOOK.md: added failure mode #7 (Telegram token scraped)
- All changes pushed to GitHub

### Pending
- Same as Apr 29 pending — nothing new added

---

## Session Log: 2026-04-29

### Done
- 11 outreach contacts marked Passed: James Chiu, Ali Vira, Shreya, Jaime, Cade, Dec, Maxine, Jeremy, Roy, Jordan, Sam
- Pedro Franceschi (Brex CEO) — Email 3 sent, CFO office workflow angle, follow-up May 2
- Danny Williams (Wealthsimple) — Referred (shared with TA team)
- JPM rejection: Area Director Blueprint role, no first round despite Tejas referral. Closed across Jobs tab + all outreach (Tejas, Jason, Monica, Austin Osborne)
- Razib Ahmed + Andrew Tulloch tasks marked done
- New outreach logged: Derek (Demand Inc), Doug (EBM AI), Neeraj (Deloitte Ventures) — network ask, AI builder PM, follow-up May 2
- George (MeetAlfred, Melbourne) — WhatsApp task added, casual warm message drafted
- Austin recruiters: 40 compiled, saved to `data/austin_recruiters.csv`. T011 updated in Tasks tab.
  - Priority contacts: Somer Hackley (exec recruiter, VP/Product), Vicente Cuadra (TEKsystems), Allen Kadilis (boutique founder), Charl Botha (Randstad)
  - DM template pending
- Seleena Juma follow-up due today — check if she shared resume with Wealthsimple + Accenture FS

### Pending
- DM template for Austin recruiters — send to priority 4 first (Somer, Vicente, Allen, Charl), then blast remaining 36
- George (MeetAlfred) WhatsApp — due today
- Seleena Juma follow-up (due today)
- VC Talent Partner DMs (5, Austin/LA) — T010, still todo
- Andrew Tulloch follow-up May 4
- Victor Skrylev follow-up May 4
- Razib Ahmed follow-up May 4
- Recruiter blitz follow-up May 4
- Derek / Doug / Neeraj follow-up May 2
- Pedro Franceschi follow-up May 2
- Video: How I built my OpenClaw agent — no date

---

## Session Log: 2026-04-27

### Done
- Fixed morning brief: "Passed", "Closed", "Referred" added to terminal statuses — no more surfacing contacts Hirsch closed out
- Removed Thomas Mann (Meta), Yufu Li (Taco Bell), Javin Chouhan (CLEAR), Bharath Raj N (Google DeepMind), Saurabh Mishra (Amazon) from Jobs sheet and memory
- Logged Razib Ahmed intros: Relay + Float — messages sent, follow-up May 4 (Outreach)
- Victor Skrylev logged to Outreach — well connected, intro to Ahmed (Venn), asked about other product roles, follow-up May 4
- Andrew Tulloch: sent email with updated resume (client names added to Focused Bets) + 3 forwardable blurbs for Levr.ai, HiloLabs, Esusu — logged to Outreach, follow-up May 4
- Recruiter blitz follow-up (~30 LI DMs): "still open to the right fintech role if anything moved" — logged, follow-up May 4
- Hannah + Lindsay (email follow-ups with resume) — logged, follow-up May 4
- Tasks marked done: LinkedIn inbounds check, Rachel Zimmerman Wealthsimple reminder
- LinkedIn post published: 3,247 CS transcripts / $2.2M ARR / bot shipped within a week — state.json updated
- Seleena Juma logged: sent resume + synopsis, she'll share with Wealthsimple + Accenture FS contacts, follow-up Apr 29
- Voice rules updated: forwardable blurb format from Razib message — pushed to GitHub

### Pending
- Seleena Juma follow-up Apr 29 (check if she's shared resume)
- Andrew Tulloch follow-up May 4
- Victor Skrylev follow-up May 4
- Razib Ahmed follow-up May 4
- Recruiter blitz follow-up May 4
- VC Talent Partner DMs (5, Austin/LA) — overdue since Apr 15, still pending
- Austin HM DMs (10, Visa/Circle/Pismo) — overdue since Apr 16, still pending
- Video: How I built my OpenClaw agent — no date

## Session Log: 2026-04-22

### Done
- Google OAuth expired (again) — fixed permanently: all Sheets scripts switched to service account auth (`sterl-sheets@studious-saga-412409.iam.gserviceaccount.com`)
- Gmail/Calendar still on OAuth — skipped for now, not critical
- Morning brief fixed: section 1 was broken (looking for D3/D7/D14 stage codes instead of Follow-Up Date column) — rewritten, pushed to GitHub
- Full outreach sheet cleanup: ~36 rows reviewed and updated
- Passed: Matas, Philman/Rippling, Sefunmi, Santosh, Jonny Stuart, James Courtney, Alia Kaussar, Andy Woods
- Stale: Jason Finkelstein, Monica Rincon, Austin Osborne (JPM — no reply)
- Followed up: James Chiu, Ali Vira, Shreya, Jaime Lopez, Cade, Dec McLaughlin, Danny Williams, Maxine Samaha, Mercury x4, Pedro Franceschi — all due Apr 25
- Vino x2 (Holt Renfrew + Canada Goose) — follow-up Apr 23
- Tejas Savalia submitted JPM referral — Jobs tab updated to "applied"
- Recruiter blitz: ~40 LinkedIn DMs sent using fintech blurb (Senior/Staff PM or HoP, Series B+ fintech)
- Recruiter blurb finalized and saved to voice_rules.md
- LinkedIn post voice rules updated (Apr 21 edits from posted content)
- All changes pushed to GitHub

### Pending
- Vino check-in tomorrow Apr 23 (Holt Renfrew + Canada Goose + Rachel Zimmerman/Wealthsimple)
- Follow-ups Apr 25: full active list (Mercury x4, Stripe x3, Ali Vira, Shreya, Danny, Dec, Pedro, James Chiu, Maxine, recruiter blitz)
- VC Talent Partners outreach (5 DMs, Austin/LA) — overdue since Apr 15
- Austin HM DMs (10, Visa/Circle/Pismo) — overdue since Apr 16
- LinkedIn profile inbounds check — overdue since Apr 17
- LinkedIn profile update (T009) — still pending
- Video: How I built my OpenClaw agent — no date

## Session Log: 2026-04-15 (evening)

### Done
- Mercury outreach: Jeremy Montes, Roy Morejon, Jordan Olesen, Sam Haddon — all sent, logged to Outreach tab with follow-up Apr 18
- voice_rules.md updated: no filler warmers, no em dashes, lowercase "hey", short broken lines, parentheticals for context, tight language ("I'm interviewing" not "I'm currently interviewing")
- Follow-up timing rule locked: 3 days from send date
- Fixed: linkedin-content-prompt.py was re-firing on already-posted content — no posted-state tracker existed
- Built `scripts/state.py` — shared cron state module (zero API calls, reads/writes logs/state.json)
- Retrofitted 3 crons to use shared state: followup-sequence (once/day), evening-nudge (4h cooldown), linkedin-content-prompt (3-day posted check)
- All pushed to GitHub

### Pending
- Venn case study due Apr 17 — not started
- Ramp next steps — end of week / early next week
- Follow-ups Apr 17: Pedro Franceschi (Brex), Danny Williams (Wealthsimple)
- Follow-ups Apr 18: Dec McLaughlin (Stripe), Ali K, Philman/Rippling, Mercury x4
- JP Morgan: Jason Finkelstein, Monica Rincon, Austin Osborne — overdue
- LinkedIn profile update (T009)
- LinkedIn post (pending)

---

## Session Log: 2026-04-15

### Done
- Venn moved to Case Study stage — received Apr 14, due Apr 17
- Dec McLaughlin (Stripe) replied — digging internally for a contact, follow-up Apr 18
- Eduardo Martinez-Barrera (Adyen recruiter) — outreached via Template 5
- Philman via Annie Liu (Rippling) — intro request sent, follow-up Apr 18
- Danny Williams (Wealthsimple) — intro request sent, follow-up Apr 17
- Pedro Franceschi (Brex CEO) — email sent + LinkedIn comment, follow-up Apr 17
- Jessica Hansen Vi (Brex recruiter) — connection request sent
- Matthew Parson (Brex) — passed
- Santosh Booluck — passed
- Ali K, CPA — replied, follow-up Apr 18
- Ramp: Yeno replied — update expected end of week or early next week
- Template 5 (recruiter cold outreach) added to outreach_templates.md
- Template 1c (casual AI-angle intro blurb) added to outreach_templates.md
- voice_rules.md: no em dashes hard rule added
- Anthropic API partial outage today ~14:53-16:01 UTC (resolved)
- Strategy locked: sniper not shotgun, 3 companies/day, 3-4 threads each

### Pending
- Venn case study due Apr 17
- Ramp next steps — end of week / early next week
- Follow-ups Apr 17: Pedro Franceschi (Brex), Danny Williams (Wealthsimple)
- Follow-ups Apr 18: Dec McLaughlin (Stripe), Ali K, Philman/Rippling
- JP Morgan follow-ups: Jason Finkelstein, Monica Rincon, Austin Osborne (overdue)
- LinkedIn profile update (T009)
- LinkedIn post (pending)

---

## Session Log: 2026-04-14

### Done
- Ramp HM interview completed — William Simmons, went exceptionally well (9/10)
- Thank-you sent via Anna + Yeno. William's action item: follow up with recruiting
- Interviews tab updated: Ramp → Complete
- Fixed interview-followup.py: added "Complete" to skip statuses
- Fixed evening-nudge.py: added nudge log (logs/evening-nudge-last.json)
- Intro blurb finalized: "senior fintech PM & founder, 4 months, $23M+ revenue & $6M fundraising"
- Job search strategy saved: Track A (Toronto in-person, Series C+ or big brand) / Track B (Remote US, $180-200K USD, contract preferred)
- Arush Agarwal / Modus logged — message sent, awaiting reply
- Replies from Gabi, Helen, Santosh, Tejas, Spencer, Julie — all marked Replied, follow-up Apr 15
- Gabi and Helen already forwarding to contacts at Stripe/Adyen
- voice_rules.md updated with Apr 14 lessons

### Pending (tomorrow Apr 15)
- Follow up: Gabi, Helen, Santosh, Tejas, Spencer, Julie
- JP Morgan follow-ups: Jason Finkelstein, Monica Rincon, Austin Osborne, Tejas Savalia
- Venn post-call thank-you + Interviews tab update
- LinkedIn profile update (T009)
- Await Ramp next steps

---

## Session Log: 2026-04-14 (late night)

### Done
- Fixed `evening-nudge.py`: added `"sent"` to `TERMINAL_STATUS` — was re-asking about already-logged outreach
- Added nudge log: cron now writes `logs/evening-nudge-last.json` with timestamp + pending list after each fire
- Both fixes pushed to GitHub

### Pending
- Ramp HM interview Apr 14 11am EST — William Simmons
- JP Morgan follow-ups (Jason Finkelstein, Monica Rincon, Austin Osborne, Tejas Savalia) — due Apr 15
- Venn post-call thank-you + Interviews tab update
- LinkedIn profile update (T009)

---

## Session Log: 2026-04-13 (evening)

### Done
- 15 outreach touches logged to sheet (Stripe x3, TLA, Avi/Boomi, Spencer Hoffman/BMF, Sefunmi/Helen/Julie/Ali K for Stripe intros, Jonny Stuart/James Courtney for Brex intro, Maxine Samaha/TLA)
- Phoenix Technologies (Tim Schulz) followed up — status updated in Interviews tab, follow-up Apr 20
- Spencer Hoffman last name updated in sheet
- Voice rules updated: no "well deserved", drop filler warmers, casual close when rapport exists
- New operating rule added: check sheet before asking Hirsch about status
- Fintech blurb drafted for Ali Vira referral (with Deloitte, HSBC, neobank, Hearth numbers)
- All outreach logged to Outreach tab with follow-up dates Apr 20
- Pushed to GitHub

### Pending
- Ramp HM interview tomorrow Apr 14 11am EST with William Simmons — PREP TONIGHT
- Venn post-call thank-you + Interviews tab update (call was today 1pm EST)
- JP Morgan follow-ups (Jason Finkelstein, Monica Rincon, Austin Osborne, Tejas Savalia) — due Apr 15
- LinkedIn profile update (T009) — still to do
- Avi message drafted but confirm if sent (logged as sent)

## Session Log: 2026-04-13 (morning)

### Done
- OAuth re-authed (file-based keyring — no passphrase going forward)
- All pending tasks pushed to Sheets (T009–T013)
- T007 merged into T009, marked done
- T001, T002, T013 marked done (per Hirsch)
- T004 + T013 merged into one video task
- T005 marked done (fintech outreach blitz complete)
- Outreach follow-ups sent: James Chiu (Cedar), Matas (Instacart), Shreya (Chime), Ali Vira (Plaid), Matthew Cavdar (Adyen)
- New outreach logged: Gabi Foschi (Adyen), Matthew Cavdar (Adyen)
- Venn meet & greet added to Interviews tab — Ahmed Shafik (co-founder), 1pm EST, Canadian business banking fintech, Series A $21.5M
- LinkedIn post drafted + edited (Anthropic cost optimization story)
- Em dash → hyphen noted as voice rule for all outreach messages

### Pending
- JP Morgan follow-ups (Jason Finkelstein, Monica Rincon, Austin Osborne, Tejas Savalia) — due Apr 15
- Ramp HM interview — Apr 14 11am EST with William Simmons
- LinkedIn profile update (T009) — still to do
- Venn post-call thank-you + update Interviews tab after call
- More Ramp-leveraging outreach to come (Hirsch's strategy, ongoing)

## Session Log: 2026-04-10 (evening)

### Done
- MEMORY.md slimmed (~50% token reduction), pipeline data moved to Sheets as source of truth
- Hearth title corrected everywhere: Senior PM, not Head of Product
- Outreach Template 3 (intro request) rewritten to match best-practice guidelines
- Interviews tab updated: Ramp → Apr 14 11am EST, William Simmons
- Contacts tab: added James Winters, Matas Sriubiskis, Yeno, Timothy Schulz
- "Where to Look Things Up" section added to MEMORY.md

### Pending (Monday)
- **OAuth token expired** — needs `gog auth add` re-auth before anything sheet-related works
- **Follow-up dates** — move James Chiu, Matas, Ali Vira, Shreya, Alia all to Mon Apr 13 in Outreach tab (pushed from this Friday)
- **Outreach blitz** — 25 messages next week, fintech focus, Ramp interview as social proof angle. Connection-based first, cold second.

---

## Known Issues

- [ ] Cron fires 16:00 UTC = 12pm EDT (not 11am) — adjust to 15:00 UTC if needed
- [ ] Sunday silence not implemented
- [ ] Anthropic key not in .env (needed for linkedin-draft.py subprocess)
