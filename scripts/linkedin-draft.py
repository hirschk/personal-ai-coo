#!/usr/bin/env python3
"""
linkedin-draft.py
Called manually with a brain dump as a CLI arg (or via stdin).
Drafts a LinkedIn post in Hirsch's voice using Claude, sends to Telegram.

Usage:
  python3 linkedin-draft.py "your messy brain dump here"
  echo "brain dump" | python3 linkedin-draft.py
"""

import os
import sys
import requests
from datetime import datetime, timezone

import anthropic

# Config
TELEGRAM_BOT_TOKEN = "8397276417:AAFelaU6_0xyF3ImUNmQ3TqW1erW4HieOY0"
TELEGRAM_CHAT_ID = "8768439197"
WORKSPACE = "/root/.openclaw/workspace"
DRAFTS_LOG = os.path.join(WORKSPACE, "logs", "linkedin-drafts.log")


def load_voice_rules():
    path = os.path.join(WORKSPACE, "voice_rules.md")
    if not os.path.exists(path):
        return ""
    rules = []
    with open(path) as f:
        in_section = False
        for line in f:
            if line.startswith("## LinkedIn Post Rules") or line.startswith("## Learned Rules"):
                in_section = True
                continue
            if line.startswith("## ") and in_section:
                in_section = False
            if in_section and line.startswith("- "):
                rules.append(line.strip())
    return "\n".join(rules)

IMAGE_SYSTEM_PROMPT = """Based on this LinkedIn post, suggest one specific, concrete image idea.
Be brief (one sentence). Think: screenshot, diagram, photo, illustration — something that would actually add signal.
Output ONLY the image suggestion, no preamble."""


def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
    }
    resp = requests.post(url, json=payload, timeout=10)
    resp.raise_for_status()
    return resp.json()


def log_draft(brain_dump, draft):
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    os.makedirs(os.path.dirname(DRAFTS_LOG), exist_ok=True)
    with open(DRAFTS_LOG, "a") as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"[{timestamp}]\n")
        f.write(f"INPUT:\n{brain_dump}\n\n")
        f.write(f"DRAFT:\n{draft}\n")


def draft_post(brain_dump):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set in environment.", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    voice_rules = load_voice_rules()
    system_prompt = f"""You are a LinkedIn ghostwriter for a senior AI product manager.

Voice rules (follow strictly):
{voice_rules}

Take the user's brain dump and extract the most post-worthy insight. Draft a LinkedIn post.
Output ONLY the post text. No intro, no \"here's a draft\", no explanation."""

    # Draft the post
    response = client.messages.create(
        model="claude-haiku-3-5-20241022",
        max_tokens=500,
        system=system_prompt,
        messages=[{"role": "user", "content": brain_dump}],
    )
    draft = response.content[0].text.strip()

    # Get image suggestion
    img_response = client.messages.create(
        model="claude-haiku-3-5-20241022",
        max_tokens=100,
        system=IMAGE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": draft}],
    )
    image_suggestion = img_response.content[0].text.strip()

    return draft, image_suggestion


def main():
    # Get brain dump from CLI arg or stdin
    if len(sys.argv) > 1:
        brain_dump = " ".join(sys.argv[1:]).strip()
    elif not sys.stdin.isatty():
        brain_dump = sys.stdin.read().strip()
    else:
        print("Usage: python3 linkedin-draft.py \"your brain dump here\"")
        print("       echo \"brain dump\" | python3 linkedin-draft.py")
        sys.exit(1)

    if not brain_dump:
        print("ERROR: No input provided.", file=sys.stderr)
        sys.exit(1)

    print(f"Drafting from: {brain_dump[:80]}{'...' if len(brain_dump) > 80 else ''}")

    try:
        draft, image_suggestion = draft_post(brain_dump)
    except Exception as e:
        print(f"ERROR generating draft: {e}", file=sys.stderr)
        sys.exit(1)

    # Log to file
    try:
        log_draft(brain_dump, draft)
        print(f"Draft saved to {DRAFTS_LOG}")
    except Exception as e:
        print(f"[warn] Could not write to drafts log: {e}", file=sys.stderr)

    # Format Telegram message
    telegram_msg = (
        "Here's your LinkedIn post:\n\n"
        f"{draft}\n\n"
        f"Image suggestion: {image_suggestion}\n\n"
        "Reply 'good' to log as posted, 'redraft [what to change]' to revise, or 'skip' to pass."
    )

    try:
        send_telegram(telegram_msg)
        print("Draft sent to Telegram.")
    except Exception as e:
        print(f"ERROR sending to Telegram: {e}", file=sys.stderr)
        # Still print the draft locally so it's not lost
        print("\n--- DRAFT (not sent) ---")
        print(draft)
        print(f"\nImage suggestion: {image_suggestion}")
        sys.exit(1)


if __name__ == "__main__":
    main()
