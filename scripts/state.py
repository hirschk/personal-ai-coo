#!/usr/bin/env python3
"""
state.py -- Shared cron state manager for Sterl OS.

Single source of truth for all cron operational state.
Reads/writes logs/state.json. Zero API calls. Microseconds to check.

Usage:
    from state import get_state, set_state, fired_today, fired_within_hours

    if fired_today("morning_brief"):
        sys.exit(0)

    # ... do the work ...

    mark_fired("morning_brief")
"""

import json
import os
from datetime import datetime, timezone, timedelta

WORKSPACE  = "/root/.openclaw/workspace"
STATE_FILE = os.path.join(WORKSPACE, "logs", "state.json")


def _load() -> dict:
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def _save(data: dict):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_state(key: str) -> dict:
    return _load().get(key, {})


def set_state(key: str, value: dict):
    data = _load()
    data[key] = value
    _save(data)


def mark_fired(key: str, extra: dict = None):
    """Record that a cron just fired."""
    now = datetime.now(timezone.utc).isoformat()
    entry = {"last_fired": now}
    if extra:
        entry.update(extra)
    data = _load()
    existing = data.get(key, {})
    existing.update(entry)
    data[key] = existing
    _save(data)


def mark_acked(key: str):
    """Record that the user acknowledged/responded to this cron's message."""
    data = _load()
    entry = data.get(key, {})
    entry["last_ack"] = datetime.now(timezone.utc).isoformat()
    data[key] = entry
    _save(data)


def fired_today(key: str) -> bool:
    """Return True if this cron already fired today (UTC date)."""
    entry = get_state(key)
    last = entry.get("last_fired")
    if not last:
        return False
    try:
        last_dt = datetime.fromisoformat(last)
        return last_dt.date() == datetime.now(timezone.utc).date()
    except Exception:
        return False


def fired_within_hours(key: str, hours: float) -> bool:
    """Return True if this cron fired within the last N hours."""
    entry = get_state(key)
    last = entry.get("last_fired")
    if not last:
        return False
    try:
        last_dt = datetime.fromisoformat(last)
        return datetime.now(timezone.utc) - last_dt < timedelta(hours=hours)
    except Exception:
        return False


def posted_within_days(key: str, days: int) -> bool:
    """Return True if last_posted for this key is within N days."""
    entry = get_state(key)
    last = entry.get("last_posted")
    if not last:
        return False
    try:
        last_dt = datetime.fromisoformat(last) if "T" in last else datetime.strptime(last, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - last_dt < timedelta(days=days)
    except Exception:
        return False
