"""
Entry point for the LLM Brain (LOCAL role).

Single-task mode:
    python run_brain_local.py --task <path-to-task.md>

Queue mode (continuous polling):
    python run_brain_local.py
    python run_brain_local.py --domain email --poll 5
    python run_brain_local.py --once    # one pass then exit
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

# Default to local role so can_execute_action() permits everything
os.environ.setdefault("AGENT_ROLE", "local")

from llm_brain.brain import LLMBrain


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the LLM Brain (local role).")
    parser.add_argument("--task", help="Process a single task file and exit.")
    parser.add_argument("--domain", help="Limit queue to one Needs_Action/ subdirectory (e.g. 'email').")
    parser.add_argument("--once", action="store_true", help="Queue mode: one polling pass then exit.")
    parser.add_argument("--poll", type=int, default=10, help="Queue poll interval in seconds.")
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

    # Queue mode
    from llm_brain.task_queue import TaskQueue
    queue = TaskQueue(brain=brain, poll_interval=args.poll)
    queue.run(domain=args.domain, once=args.once)
    return 0


if __name__ == "__main__":
    sys.exit(main())
