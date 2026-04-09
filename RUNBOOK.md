# RUNBOOK.md — Known Failure Modes

Things that break and how to fix them. Add new ones here when they're discovered.

---

## 1. Apify Token Expires

**Symptom:** Job brief doesn't fire. `job-discovery.log` shows `ApifyApiError: User was not found or authentication token is not valid`

**Fix:**
1. Go to console.apify.com → Settings → Integrations → API tokens
2. Copy new token
3. Tell Sterl: "Here's the new Apify token: apify_api_xxx"
4. Sterl updates `job-discovery-apify.py` and `/etc/environment`

**Prevention:** Apify tokens don't auto-expire — this happens when account is reset or token is revoked. Check the console if it breaks.

---

## 2. Anthropic API Credits Run Out

**Symptom:** Every message fails with rate limit or billing error. OpenClaw gateway logs show 429/402 errors.

**Fix:**
1. Go to console.anthropic.com → Billing → Add credits
2. Tier 2 requires $25+ balance — top up to at least $25

**Prevention:** Set a spend alert in Anthropic console. Current model (Sonnet) + caching keeps costs low but monitor weekly.

---

## 3. GitHub Push Fails / Wrong Account

**Symptom:** `git push` fails with auth error or pushes to wrong repo (hirschkeshav-lab instead of hirschk)

**Fix:**
1. Check remote: `cd /root/.openclaw/workspace && git remote -v`
2. Should show: `git@github.com:hirschk/personal-ai-coo.git`
3. Check SSH: `ssh -T git@github.com` → should say `Hi hirschk/personal-ai-coo!`
4. If wrong: `git remote set-url origin git@github.com:hirschk/personal-ai-coo.git`

**Auth method:** SSH deploy key at `/root/.ssh/sterl_github` — does NOT expire. No tokens needed.

**Prevention:** SSH deploy key is permanent. This should only break if the key is deleted from GitHub or `/root/.ssh/sterl_github` is removed.

---

## 4. Google OAuth Token Fails

**Symptom:** Scripts fail with `RefreshError: invalid_scope` or `Token has been expired or revoked`

**Fix:**
1. Tell Sterl: "Re-auth Google"
2. Sterl generates an auth URL
3. Open URL, sign in as hirschkeshav@gmail.com
4. Paste the code back to Sterl
5. Sterl saves new token to `config/gog-token.json`

**Scopes needed:** Sheets (write) + Gmail (readonly) + Calendar (readonly)

**Prevention:** OAuth refresh tokens don't expire unless revoked. This breaks if Google revokes the token (rare) or if the app is removed from authorized apps.

---

## 5. Cron Fires at Wrong Time (DST)

**Symptom:** Brief arrives at 12pm instead of 11am (or other 1-hour drift)

**Cause:** Crons are in UTC. EST = UTC-5, EDT = UTC-4. When clocks change in March, 16:00 UTC shifts from 11am EST to 12pm EDT.

**Current state:** Cron fires at 16:00 UTC = 12pm EDT (as of Apr 2026)

**Fix:** Change to 15:00 UTC for true 11am EDT:
```bash
crontab -e
# Change: 0 16 * * 1,3,5 → 0 15 * * 1,3,5
```

---

## 6. MEMORY.md Out of Sync

**Symptom:** Sterl doesn't know about recent work, gives stale answers about what's built

**Fix:**
1. Tell Sterl: "Read the commit history and update MEMORY.md"
2. Or: "Here's what changed — update your memory"

**Prevention:** Memory standup rule (in SOUL.md) — Sterl writes to MEMORY.md at end of any session where code was written or pushed.

---

## 7. Dual Instance / Double Billing

**Symptom:** API costs spike unexpectedly. Two OpenClaw instances running simultaneously (e.g. Mac + VPS).

**Fix:** Kill the non-VPS instance. Only one instance should ever run.

**Prevention:** OpenClaw should only run on the VPS (67.205.179.96). Do not run it locally on the Mac.

---

## Config Freeze — Do Not Change

The following config is intentionally set and optimized. Do not change without a strong reason:

- `heartbeat.every: "0m"` — heartbeats OFF. Cron jobs handle all scheduled tasks. Re-enabling adds cost with no benefit.
- `params.cacheRetention: "long"` — maximizes cache hits, reduces input token costs significantly.
- `params.maxTokens: 1500` — caps output tokens per response.
- `cron/jobs.json` — delivery.to is set to `8768439197` on all jobs. Already correct.
- Single VPS instance only — never run OpenClaw on Mac simultaneously.

---

*Add new failure modes here as they're discovered.*
