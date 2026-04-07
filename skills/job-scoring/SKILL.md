---
name: job-scoring
description: Score and rank job opportunities against candidate profile using weighted matching
---

# Job Scoring Logic

## Scoring Formula

```
priority_score = (0.4 × fit_score) + (0.4 × network_score) + (0.2 × recency_score)
```

Range: **0.0–1.0** (higher is better)

---

## Fit Score (0.4 weight)

Matches job against target roles, industries, and seniority.

**Target Roles:**
- Head of Product (100% match)
- VP Product (95% match)
- Director of Product (90% match)
- Senior Product Manager (70% match)
- Product Manager (40% match)
- Other (0% match)

**Target Industries:**
- Fintech (100% match)
- AI-native (100% match)
- AI-forward (90% match)
- Tech/SaaS (70% match)
- Enterprise (60% match)
- Other (10% match)

**Seniority Alignment:**
- Candidate has 10 YOE; roles targeting 5-12 YOE = full match
- Roles targeting 0-4 YOE = 40% match
- Roles targeting 13+ YOE = 70% match

**Calculation:**
```
fit_score = (0.5 × role_match) + (0.3 × industry_match) + (0.2 × seniority_match)
```

---

## Network Score (0.4 weight)

Matches job company against Hirsch's 4,261 LinkedIn connections.

**Scoring Tiers:**

| Connection Type | Score |
|---|---|
| 1st degree at company in product/PM role | 1.0 |
| 1st degree at company in recruiting/talent role | 0.8 |
| 1st degree at company (any role) | 0.6 |
| No 1st degree connection | 0.0 |

**Network Score** = connection_tier_score

---

## Recency Score (0.2 weight)

Jobs posted recently get higher priority.

| Posted | Score |
|---|---|
| < 48 hours | 1.0 |
| 2-4 days | 0.8 |
| 5-7 days | 0.5 |
| 8-14 days | 0.2 |
| > 14 days | 0.0 |

---

## Priority Ranking

| Priority Score | Rank | Action |
|---|---|---|
| 0.85–1.0 | Top Tier | Draft outreach immediately, lead with network |
| 0.70–0.84 | Tier 1 | Draft outreach, schedule for next check-in |
| 0.55–0.69 | Tier 2 | Monitor, draft if still open after 3 days |
| 0.40–0.54 | Tier 3 | Keep in list, review weekly |
| < 0.40 | Pass | Skip unless fit score is perfect |

---

## Example Scoring

### Example 1: Head of Product @ Fintech, 1st-degree connection

```
fit_score = (0.5 × 1.0) + (0.3 × 1.0) + (0.2 × 1.0) = 1.0
network_score = 1.0 (1st degree, PM role)
recency_score = 1.0 (posted yesterday)

priority_score = (0.4 × 1.0) + (0.4 × 1.0) + (0.2 × 1.0) = 1.0
→ TOP TIER — Draft outreach immediately
```

### Example 2: VP Product @ AI-native, no connection, 5 days old

```
fit_score = (0.5 × 0.95) + (0.3 × 1.0) + (0.2 × 1.0) = 0.975
network_score = 0.0 (no connection)
recency_score = 0.5 (posted 5 days ago)

priority_score = (0.4 × 0.975) + (0.4 × 0.0) + (0.2 × 0.5) = 0.49
→ TIER 3 — Monitor, skip for now
```

### Example 3: Senior PM @ Fintech, 1st-degree recruiter connection, 2 days old

```
fit_score = (0.5 × 0.7) + (0.3 × 1.0) + (0.2 × 1.0) = 0.85
network_score = 0.8 (1st degree, recruiting)
recency_score = 0.8 (posted 2 days ago)

priority_score = (0.4 × 0.85) + (0.4 × 0.8) + (0.2 × 0.8) = 0.82
→ TIER 1 — Draft outreach
```

---

## Implementation Notes

**Company Name Normalization:**
- Fuzzy match job company against network.md using 80%+ similarity threshold
- "Google LLC" → "Google", "Meta Platforms" → "Meta"
- Flag ambiguous matches for manual review

**Edge Cases:**
- If job posting is locked (no apply button), mark as cold immediately
- If job is remote but candidate prefers on-site (or vice versa), apply 0.8x multiplier to fit_score
- If company is in candidate's "pass" list (bankrupt, unethical, toxic culture), return 0.0

**Output Format:**
```json
{
  "job_id": "linkedin_job_123",
  "title": "Head of Product",
  "company": "Fintech Co",
  "priority_score": 0.92,
  "fit_score": 0.95,
  "network_score": 1.0,
  "recency_score": 0.8,
  "rank": "Top Tier",
  "network_path": "Sam Chen (1st degree, PM @ Fintech Co)",
  "action": "Draft outreach immediately"
}
```
