"""
Entry point for the LLM Brain (CLOUD role).

The cloud agent reads tasks and drafts actions, but never directly sends emails,
posts to socials, confirms invoices, or registers payments. Those are blocked
by agent_config.can_execute_action() — the brain must use the *_draft variants
and let the local agent execute after human approval.

Single-task mode:
    set AGENT_ROLE=cloud && python run_brain_cloud.py --task <path>

Queue mode (continuous):
    set AGENT_ROLE=cloud && python run_brain_cloud.py
    set AGENT_ROLE=cloud && python run_brain_cloud.py --domain email --once
"""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

# Windows consoles default to cp1252; models routinely emit characters outside
# that range (em-dashes, non-breaking hyphens, smart quotes). Reconfigure to
# UTF-8 with replacement so print() never crashes the runner.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

# Force cloud role — the brain's gating, system prompt branching, and tool
# executor all key off this env var. Setting it here ensures the safe default
# even if the caller forgot to export it.
os.environ["AGENT_ROLE"] = "cloud"

from llm_brain.brain import LLMBrain


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the LLM Brain (cloud role).")
    parser.add_argument("--task", help="Process a single task file and exit.")
    parser.add_argument("--domain", help="Limit queue to one Needs_Action/ subdirectory.")
    parser.add_argument("--once", action="store_true", help="Queue mode: one polling pass then exit.")
    parser.add_argument("--poll", type=int, default=30, help="Queue poll interval in seconds.")
    args = parser.parse_args()

    brain = LLMBrain()

    if args.task:
        task_path = Path(args.task)
        if not task_path.exists():
            print(f"Task file not found: {task_path}", file=sys.stderr)
            return 1
        summary = brain.process_task(task_path)
        print("\n===== BRAIN SUMMARY =====")
        print(summary)
        return 0

    from llm_brain.task_queue import TaskQueue
    queue = TaskQueue(brain=brain, poll_interval=args.poll)
    queue.run(domain=args.domain, once=args.once)
    return 0


if __name__ == "__main__":
    sys.exit(main())
