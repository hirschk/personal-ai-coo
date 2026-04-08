# SKILL.md — LinkedIn Agent

## Purpose
Draft and track LinkedIn content for Hirsch Keshav. Maintain a consistent 3x/week posting cadence (Mon/Wed/Fri). Posts reflect Hirsch's PM voice: sharp, understated, data-driven.

## Scripts (all in `/root/.openclaw/workspace/scripts/`)
| Script | Trigger | What it does |
|---|---|---|
| `linkedin-content-prompt.py` | Cron Mon/Wed/Fri 6pm EDT | Prompts Hirsch for a brain dump, checks memory for hook ideas |
| `linkedin-draft.py` | Manual | `python3 linkedin-draft.py "brain dump"` → Claude-drafted post |
| `voice-update.py` | Manual | Paste original + edited → extracts voice rule → appends to voice_rules.md |

## Reads
- `context.md` (this directory) — voice rules, cadence, draft patterns
- `/root/.openclaw/workspace/scripts/voice_rules.md` — current voice rules (primary source of truth)

## Writes
- Telegram: draft posts for Hirsch review
- `/root/.openclaw/workspace/scripts/voice_rules.md` — updated by voice-update.py

## Voice Rules (canonical source: `voice_rules.md`)
- Short sentences. No em dashes.
- No filler openers: no "Hope you're well", no "Circling back", no "Excited to share"
- No corporate buzzwords
- PM-native language: "shipped", "mapped to outcomes", "found in the data"
- Slightly understated — tighten, don't add colour
- End with a real question, not rhetorical
- No dramatic openers

## Content Cadence
- **Mon/Wed/Fri** — 3 posts per week
- Format: brain dump from Hirsch → drafted by Claude