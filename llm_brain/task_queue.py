"""
Task queue — pull tasks from Needs_Action/ and feed them to the brain.

Wraps ClaimManager (atomic os.rename) and LLMBrain (Gemini agentic loop) in a
polling loop. The brain processes one task at a time; release_done() moves the
file to Done/<domain>/ on completion.

If the brain creates drafts (Pending_Approval/Email_Drafts/ etc.) during
processing, those stay where they are — the queue only manages the source task
file's lifecycle.
"""

import signal
import time
from collections import deque
from pathlib import Path
from typing import Optional

from production_utils import get_structured_logger
from claim_manager import ClaimManager

from llm_brain import config
from llm_brain.brain import LLMBrain
from llm_brain.approval_handler import ApprovalHandler


logger = get_structured_logger("llm_brain.task_queue")


class TaskQueue:
    """Pulls tasks from Needs_Action/ and dispatches them to the brain."""

    def __init__(self, brain: Optional[LLMBrain] = None, poll_interval: int = 10):
        self.brain = brain or LLMBrain()
        self.claim_manager = ClaimManager()
        self.approval_handler = ApprovalHandler()
        self.poll_interval = poll_interval
        self._stop = False
        self._recent_starts: deque[float] = deque()

    def _domain_of(self, claimed_path: Path) -> str:
        """Derive the original Needs_Action/<domain>/ from the claimed file's name."""
        needs_action = self.claim_manager.needs_action_dir
        # Walk Needs_Action subdirs and match by stem — the file is no longer there,
        # so we look up the domain folders that exist and pick the first that matches
        # naming conventions. Fallback to "unknown" if we can't tell.
        for sub in needs_action.iterdir():
            if sub.is_dir():
                # We can't query the original path post-claim; use the convention:
                # domain comes from the file's parent dir at claim time. The caller
                # passes that in via process_one(), so this is a fallback only.
                pass
        return ""

    def _rate_limit_block(self) -> None:
        """Sleep if we've hit MAX_TASKS_PER_HOUR. Trims old timestamps."""
        now = time.time()
        cutoff = now - 3600
        while self._recent_starts and self._recent_starts[0] < cutoff:
            self._recent_starts.popleft()
        if len(self._recent_starts) >= config.MAX_TASKS_PER_HOUR:
            oldest = self._recent_starts[0]
            wait = (oldest + 3600) - now
            if wait > 0:
                logger.warning(
                    f"Hourly task limit ({config.MAX_TASKS_PER_HOUR}) reached. "
                    f"Sleeping {wait:.0f}s."
                )
                time.sleep(wait)

    def _process_one(self, task_path: Path) -> bool:
        """
        Claim, process, release one task. Returns True if a task was actually handled.
        """
        domain = task_path.parent.name if task_path.parent != self.claim_manager.needs_action_dir else ""

        claimed = self.claim_manager.claim(task_path)
        if claimed is None:
            return False

        self._recent_starts.append(time.time())
        try:
            summary = self.brain.process_task(claimed)
            logger.info(f"[{claimed.name}] {summary[:200]}")
        except Exception as e:
            logger.error(f"Brain raised on {claimed.name}: {e}", exc_info=True)
            # Release back so another agent / future run can retry
            self.claim_manager.release_back(claimed, domain=domain)
            return True

        # If the brain requested human approval during this task, park it
        # instead of marking done. The resume scan will pick it back up after
        # the approval is granted/rejected.
        approval_info = self.brain._executor.pending_approval
        if approval_info:
            self.approval_handler.park(claimed, summary, approval_info, domain=domain)
        else:
            self.claim_manager.release_done(claimed, domain=domain)
        return True

    def _resume_scan(self) -> int:
        """Find parked tasks whose approval is now resolved and re-queue them."""
        resumable = self.approval_handler.find_resumable()
        if not resumable:
            return 0
        for entry in resumable:
            self.approval_handler.prepare_resume(entry)
        logger.info(f"Resumed {len(resumable)} task(s) after approval decision.")
        return len(resumable)

    def tick(self, domain: Optional[str] = None) -> int:
        """One pass: first resume any parked-and-approved tasks, then process Needs_Action."""
        self._resume_scan()
        tasks = self.claim_manager.list_available(domain=domain)
        if not tasks:
            return 0

        handled = 0
        for task in tasks:
            if self._stop:
                break
            self._rate_limit_block()
            if self._process_one(task):
                handled += 1
        return handled

    def run(self, domain: Optional[str] = None, once: bool = False) -> None:
        """Continuous polling loop. Set once=True for a single pass."""
        signal.signal(signal.SIGINT, self._handle_sigint)
        scope = f"domain={domain}" if domain else "all domains"
        logger.info(
            f"TaskQueue starting ({scope}, poll={self.poll_interval}s, "
            f"max/hr={config.MAX_TASKS_PER_HOUR}, once={once})"
        )

        while not self._stop:
            handled = self.tick(domain=domain)
            if handled:
                logger.info(f"Tick handled {handled} task(s).")
            if once:
                break
            time.sleep(self.poll_interval)

        logger.info("TaskQueue stopped.")

    def _handle_sigint(self, signum, frame):
        logger.info("SIGINT received, draining current task and stopping.")
        self._stop = True
