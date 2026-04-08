#!/usr/bin/env python3
"""
router.py -- Sterl OS Orchestration Layer

Usage:
  From cron (direct routing):
    python3 router.py --agent job-search --task daily-brief
    python3 router.py --agent linkedin --task content-prompt
    python3 router.py --agent ideas --task structure-pending
    python3 router.py --agent session --task close

  From user message (intent classification):
    python3 router.py --message "draft outreach for job 3"
    python3 router.py --message "capture idea: build a finance tracker"
    python3 router.py --message "draft linkedin post about AI agents"
"""

import argparse
import subprocess
import sys
import logging
from pathlib import Path

WORKSPACE = Path("/root/.openclaw/workspace")
SCRIPTS   = WORKSPACE / "scripts"
LOGS      = WORKSPACE / "logs"

LOGS.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [router] %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOGS / "router.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("router")

TASK_MAP = {
    ("job-search", "daily-brief"):       SCRIPTS / "cron-job-discovery.sh",
    ("job-search", "followup-sequence"): SCRIPTS / "followup-sequence.py",
    ("job-search", "gmail-check"):       SCRIPTS / "gmail-reply-check.py",
    ("job-search", "afternoon-checkin"): SCRIPTS / "afternoon-checkin.py",
    ("job-search", "evening-nudge"):     SCRIPTS / "evening-nudge.py",
    ("linkedin",   "content-prompt"):    SCRIPTS / "linkedin-content-prompt.py",
    ("ideas",      "structure-pending"): SCRIPTS / "ideas-structure.py",
    ("ideas",      "friday-checkin"):    SCRIPTS / "friday-checkin.py",
    ("session",    "close"):             SCRIPTS / "session-close.py",
}

JOB_KEYWORDS      = {"job", "outreach", "interview", "apply", "followup", "pipeline", "recruiter", "role", "resume"}
LINKEDIN_KEYWORDS = {"linkedin", "post", "content"}
IDEAS_KEYWORDS    = {"idea", "project", "capture"}


def classify_message(message):
    text = message.lower()
    words = set(text.replace("-", " ").split())
    if "follow up" in text:
        return ("job-search", "daily-brief")
    if "draft post" in text:
        return ("linkedin", "content-prompt")
    if words & LINKEDIN_KEYWORDS:
        return ("linkedin", "content-prompt")
    if words & IDEAS_KEYWORDS:
        return ("ideas", "structure-pending")
    if words & JOB_KEYWORDS:
        return ("job-search", "daily-brief")
    return ("job-search", "daily-brief")


def run_script(script_path, message=None):
    path = Path(script_path)
    if not path.exists():
        log.error(f"Script not found: {path}")
        return 1
    if path.suffix == ".py":
        cmd = [sys.executable, str(path)]
    elif path.suffix == ".sh":
        cmd = ["/bin/bash", str(path)]
    else:
        cmd = [str(path)]
    if message:
        cmd.extend(["--message", message])
    log.info(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, cwd=str(SCRIPTS))
        log.info(f"Exited {result.returncode}: {path.name}")
        return result.returncode
    except Exception as e:
        log.error(f"Failed to run {path.name}: {e}")
        return 1


def main():
    parser = argparse.ArgumentParser(description="Sterl OS Router")
    parser.add_argument("--agent",   help="Agent name")
    parser.add_argument("--task",    help="Task name")
    parser.add_argument("--message", help="Free-text message to classify and route")
    args = parser.parse_args()

    if args.message:
        agent, task = classify_message(args.message)
        log.info(f"Classified message to agent={agent}, task={task}")
        script = TASK_MAP.get((agent, task))
        if not script:
            log.error(f"No script mapped for ({agent}, {task})")
            sys.exit(1)
        sys.exit(run_script(script, message=args.message))

    elif args.agent and args.task:
        key = (args.agent, args.task)
        script = TASK_MAP.get(key)
        if not script:
            log.error(f"Unknown agent/task: {args.agent}/{args.task}")
            log.info(f"Known tasks: {list(TASK_MAP.keys())}")
            sys.exit(1)
        log.info(f"Direct route: agent={args.agent}, task={args.task}")
        sys.exit(run_script(script))

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
