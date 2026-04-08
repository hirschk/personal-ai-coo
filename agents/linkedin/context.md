# LinkedIn — Context (domain slice from MEMORY.md)
_Last synced: 2026-04-08_

---

## Voice Rules
(Canonical source: `/root/.openclaw/workspace/scripts/voice_rules.md`)

- Short sentences. No em dashes.
- No filler openers — no "Hope you're well", no "Circling back", no "Excited to share"
- No corporate buzzwords
- PM-native: "shipped", "mapped to outcomes", "found in the data"
- Slightly understated. Tighten, don't add colour.
- Ends with a real question, not rhetorical.
- No dramatic openers.

---

## Content Cadence
- **3x/week** — Monday, Wednesday, Friday
- Prompt fires at **6pm EDT** (23:00 UTC) on Mon/Wed/Fri
- Flow: Hirsch brain dumps → `linkedin-draft.py` → Claude draft → Hirsch reviews → posts manually

---

## How to Draft Posts
1. Prompt Hirsch for a brain dump on the topic
2. Run: `python3 /root/.openclaw/workspace/scripts/linkedin-draft.py "brain dump text"`
3. Claude drafts a post following voice_rules.md
4. Send draft to Telegram for Hirsch review
5. Hirsch posts manually on LinkedIn

## Voice Rules File Location
`/root/.openclaw/workspace/scripts/voice_rules.md`

To update voice rules after Hirsch edits a post:
`python3 /root/.openclaw/workspace/scripts/voice-update.py`
(paste original + edited → extracts rule → appends to voice_rules.md)
