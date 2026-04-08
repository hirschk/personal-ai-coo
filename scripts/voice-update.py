#!/usr/bin/env python3
"""
voice-update.py — Extract a voice rule from an original vs. edited draft pair.

Usage:
  python3 voice-update.py "original draft" "edited draft"
  python3 voice-update.py          (interactive mode)
"""

import os
import sys
from datetime import datetime, timezone

import anthropic

WORKSPACE = "/root/.openclaw/workspace"
VOICE_RULES_PATH = os.path.join(WORKSPACE, "voice_rules.md")
MEMORY_PATH = os.path.join(WORKSPACE, "MEMORY.md")

SYSTEM_PROMPT = (
    "You are analyzing two versions of a message draft — an original and an edited version.\n"
    "Extract ONE clear, reusable voice rule that explains what changed and why.\n\n"
    "Format: A single sentence starting with a verb. Examples:\n"
    '- "Remove filler openers like \'Hope you\'re well\'"\n'
    '- "Use \'my background\' instead of listing credentials inline"\n'
    '- "End with a direct question, not an open offer"\n'
    '- "Keep the ask to one sentence — don\'t explain the ask"\n\n'
    "Output ONLY the rule. No explanation, no intro."
)


def get_multiline_input(prompt: str) -> str:
    """Read multi-line input until two consecutive blank lines (or EOF)."""
    print(prompt)
    lines = []
    blank_count = 0
    try:
        while True:
            line = input()
            if line == "":
                blank_count += 1
                if blank_count >= 2:
                    break
                lines.append(line)
            else:
                blank_count = 0
                lines.append(line)
    except EOFError:
        pass
    # Strip trailing blank lines collected before double-enter
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def extract_rule(original: str, edited: str) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set.", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    user_msg = f"ORIGINAL:\n{original}\n\nEDITED:\n{edited}"

    response = client.messages.create(
        model="claude-haiku-3-5-20241022",
        max_tokens=150,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )
    return response.content[0].text.strip()


def append_to_voice_rules(rule: str):
    """Append rule under '## Learned Rules (from edits)' section."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    new_entry = f"- {rule}  _(added {today})_"

    if not os.path.exists(VOICE_RULES_PATH):
        print(f"WARNING: {VOICE_RULES_PATH} not found — skipping voice_rules update.", file=sys.stderr)
        return

    with open(VOICE_RULES_PATH) as f:
        content = f.read()

    learned_header = "## Learned Rules (from edits)"
    placeholder = "_(none yet — added automatically when Hirsch pastes edited drafts)_"

    if learned_header not in content:
        # Append section at end
        content = content.rstrip() + f"\n\n{learned_header}\n{new_entry}\n"
    elif placeholder in content:
        # Replace placeholder with first real rule
        content = content.replace(placeholder, new_entry)
    else:
        # Find end of Learned Rules section and append
        idx = content.find(learned_header)
        # Find next ## section after learned_header (if any)
        rest_start = idx + len(learned_header)
        next_section = content.find("\n## ", rest_start)
        if next_section == -1:
            content = content.rstrip() + f"\n{new_entry}\n"
        else:
            content = content[:next_section] + f"\n{new_entry}" + content[next_section:]

    with open(VOICE_RULES_PATH, "w") as f:
        f.write(content)


def append_to_memory(rule: str):
    """Append rule to MEMORY.md under the LinkedIn Voice Rules section."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    new_entry = f"- {rule}  _(learned {today})_"

    if not os.path.exists(MEMORY_PATH):
        print(f"WARNING: {MEMORY_PATH} not found — skipping MEMORY.md update.", file=sys.stderr)
        return

    with open(MEMORY_PATH) as f:
        content = f.read()

    # Try to find a LinkedIn Voice Rules section
    markers = [
        "## LinkedIn Voice Rules",
        "### LinkedIn Voice Rules",
        "## Voice Rules",
        "### Voice Rules",
    ]
    insert_after = None
    for marker in markers:
        if marker in content:
            insert_after = marker
            break

    if insert_after:
        idx = content.find(insert_after)
        # Find next blank line + content after header
        rest_start = idx + len(insert_after)
        next_section = content.find("\n## ", rest_start)
        if next_section == -1:
            content = content.rstrip() + f"\n{new_entry}\n"
        else:
            content = content[:next_section] + f"\n{new_entry}" + content[next_section:]
    else:
        # Append at the end with a new section
        content = content.rstrip() + f"\n\n## LinkedIn Voice Rules (Learned)\n{new_entry}\n"

    with open(MEMORY_PATH, "w") as f:
        f.write(content)


def main():
    if len(sys.argv) == 3:
        original = sys.argv[1].strip()
        edited = sys.argv[2].strip()
    elif len(sys.argv) == 1:
        original = get_multiline_input("Paste ORIGINAL draft (then press Enter twice):")
        print()
        edited = get_multiline_input("Paste EDITED version (then press Enter twice):")
    else:
        print("Usage: python3 voice-update.py \"original\" \"edited\"")
        print("       python3 voice-update.py  (interactive)")
        sys.exit(1)

    if not original or not edited:
        print("ERROR: Both original and edited drafts are required.", file=sys.stderr)
        sys.exit(1)

    print("Extracting voice rule...")
    rule = extract_rule(original, edited)

    append_to_voice_rules(rule)
    append_to_memory(rule)

    print(f"Voice rule learned: {rule}")


if __name__ == "__main__":
    main()
