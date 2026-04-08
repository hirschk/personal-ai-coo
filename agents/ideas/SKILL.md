# SKILL.md — Ideas Agent

## Purpose
Capture, structure, and activate Hirsch's ideas. Prevent good ideas from dying in a queue. Run a lightweight Ideas OS: capture raw → structure with context → surface for action.

## Scripts (all in `/root/.openclaw/workspace/scripts/`)
| Script | Trigger | What it does |
|---|---|---|
| `ideas-capture.py` | Manual | `python3 ideas-capture.py "idea"` → logs to ideas-pending.json + Sheets + Telegram ack |
| `ideas-structure.py` | Cron daily 7pm EDT | Structures pending ideas with Claude, silent if queue is empty |
| `friday-checkin.py` | Cron Friday 5:45pm EDT | Weekly recap across all domains: jobs, outreach, ideas, LinkedIn |

## Reads
- `context.md` (this directory) — pending ideas, active projects, Ideas OS flow
- `/root/.openclaw/workspace/scripts/ideas-pending.json` — raw unstructured idea queue
- Google Sheet tab: Ideas (`1o6XXLhpxFVZL5SlDKP8a56Y17brgmD7HWzAGe1Ei4Co`)

## Writes
- `/root/.openclaw/workspace/scripts/ideas-pending.json` — pops ideas after structuring
- Google Sheet (Ideas tab) — structured idea entries
- Telegram: structured idea summaries, Friday recap

## Ideas OS Flow
```
Capture (raw text)
    ↓
ideas-pending.json (queue)
    ↓
ideas-structure.py (nightly — Claude structures + categorizes)
    ↓
Google Sheet Ideas tab (structured, tagged)
    ↓
friday-checkin.py (weekly — surface actionable items)
    ↓
Activate (Hirsch picks one to run with)
```

## Active Projects
- **Personal Finance Assistant** — manages cash flow and runway. Captured Apr 8. Pending structuring.

## Rules
- Never drop an idea unless Hirsch explicitly says: skip, park, or done.
- Friday check-in always ends with: "Which idea gets a green light this week?"
