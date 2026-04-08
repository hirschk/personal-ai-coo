# SKILL.md — Job Search Agent

## Purpose
Find roles, score against network and candidate profile, draft outreach, manage the active pipeline, and handle follow-up sequences.

## Scripts (all in `/root/.openclaw/workspace/scripts/`)
| Script | Trigger | What it does |
|---|---|---|
| `job-discovery-apify.py` | Via cron-job-discovery.sh | Apify scrape → score → Sheets → Telegram brief |
| `cron-job-discovery.sh` | Cron Mon/Wed/Fri 12pm EDT | Wrapper that runs job-discovery-apify.py |
| `followup-sequence.py` | Cron daily 9:30am EDT | Day 3/5/7/14 follow-up drafts, marks Stale at Day 15 |
| `gmail-reply-check.py` | Cron every 2h | Gmail reply detection + interview thank-you check |
| `afternoon-checkin.py` | Cron daily 5:30pm EDT | Nudge if unactioned jobs + <3 sent today |
| `evening-nudge.py` | Cron daily 6pm EDT | Evening nudge, silent if pipeline is clear |
| `draft-outreach.py` | Manual | `python3 draft-outreach.py 3` or `--intro "Name"` |
| `show-drafts.py` | Manual | Sends all 5 outreach drafts to Telegram |
| `recruiter-response.py` | Manual | `python3 recruiter-response.py "Company"` |

## Reads
- `context.md` (this directory) — pipeline state, contacts, scoring rules
- `/root/.openclaw/workspace/candidate_profile.md` — full candidate profile
- `/root/.openclaw/workspace/network.md` — network connections for warm intros
- `/root/.openclaw/workspace/scripts/voice_rules.md` — tone/style rules for outreach

## Writes
- **Google Sheet** `1o6XXLhpxFVZL5SlDKP8a56Y17brgmD7HWzAGe1Ei4Co`: tabs Jobs, Interviews, Outreach
- `/root/.openclaw/workspace/scripts/jobs-today.json` — today's scored jobs
- `/root/.openclaw/workspace/scripts/seen-jobs.json` — FIFO 500-key dedup cache
- `/root/.openclaw/workspace/logs/` — per-script log files

## Scoring Formula
```
score = (role_match * 0.40) + (industry_match * 0.30) + (network_warmth * 0.20) + (seniority_match * 0.10)
```
- role_match: title similarity to Head/VP/Director of Product
- industry_match: fintech / AI-native / AI-forward
- network_warmth: 1st-degree > 2nd-degree > cold
- seniority_match: IC-level vs director vs VP

## Follow-Up Cadence
- Day 3: light touch — "wanted to follow up"
- Day 5: add a hook (something relevant about their product)
- Day 7: final nudge before going quiet
- Day 14: re-engage with new angle
- Day 15+: mark Stale in Outreach sheet

## Key Rules
- **Carry-Forward Rule**: if Hirsch doesn't action something, carry it forward. Never drop unless Hirsch confirms: pass, done, or park.
- **Interview Follow-Up Protocol**: after any interview — fire thank-you draft within 2h via Calendar detection. Re-fire at 24h if not confirmed sent.
- **Defense SaaS Role (James Winters)**: DO NOT mention Claude/OpenClaw. 1099 contract, tax treaty TBD.
