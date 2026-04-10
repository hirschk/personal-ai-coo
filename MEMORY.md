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
- **Google OAuth:** Sheets (write) + Gmail (readonly) + Calendar (readonly)
- **Apify token:** in `/root/.openclaw/workspace/.env` and `/etc/environment`

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

1. **Carry-Forward:** never drop anything unless Hirsch says pass/done/park
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

## Known Issues

- [ ] Cron fires 16:00 UTC = 12pm EDT (not 11am) — adjust to 15:00 UTC if needed
- [ ] Sunday silence not implemented
- [ ] Anthropic key not in .env (needed for linkedin-draft.py subprocess)
