"""
Dry-test for the LLM Brain park/resume cycle.

Uses a stub LLMBrain that simulates an approval request without calling Gemini.
Verifies:
  1. Tasks that request approval are parked to Pending_Approval/ with sidecar.
  2. find_resumable() returns the parked task once the Approval MCP says approved.
  3. prepare_resume() moves the task back to Needs_Action/ with a resume marker.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))


class StubBrain:
    """Fake brain that returns canned summaries and primes the executor state."""

    def __init__(self):
        self._executor = MagicMock()
        self._executor.pending_approval = None
        self._executor.reset_task_state = lambda: None
        self._next_summary = "ok"
        self._next_approval = None

    def queue_response(self, summary, approval_info=None):
        self._next_summary = summary
        self._next_approval = approval_info

    def process_task(self, task_path):
        # Mimic the real brain's behavior: it'd set pending_approval inside execute()
        self._executor.pending_approval = self._next_approval
        return self._next_summary


class TestParkResume(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="brain_park_test_")
        os.environ["VAULT_PATH"] = self.tmp
        os.environ["AGENT_ROLE"] = "local"
        os.environ.setdefault("GEMINI_API_KEY", "stub-key-for-test")

        # Reload modules so they pick up the new VAULT_PATH env
        for mod in list(sys.modules):
            if mod.startswith("llm_brain") or mod in {"agent_config", "claim_manager"}:
                del sys.modules[mod]

        from llm_brain.task_queue import TaskQueue
        from llm_brain.approval_handler import ApprovalHandler

        self.brain = StubBrain()
        self.queue = TaskQueue(brain=self.brain, poll_interval=1)
        self.handler = ApprovalHandler()

        # Seed a task
        task_dir = Path(self.tmp) / "Needs_Action" / "email"
        task_dir.mkdir(parents=True, exist_ok=True)
        self.task_path = task_dir / "needs_approval.md"
        self.task_path.write_text("# pretend this needs approval\nAmount: $750\n")

    def test_park_then_resume_approved(self):
        # Stub brain will signal an approval request
        self.brain.queue_response(
            summary="Asked human approval for the $750 payment.",
            approval_info={
                "request_id": "req-test-001",
                "action": "register_payment",
                "amount": 750,
                "recipient": "Vendor Co",
                "reason": "Above auto-approve threshold",
            },
        )

        # Process once — task should be parked, not marked done
        with patch.object(self.handler, "_check_approval", return_value="pending"):
            handled = self.queue.tick(domain="email")
        self.assertEqual(handled, 1, "task should have been handled")

        parked = list((Path(self.tmp) / "Pending_Approval" / "email").glob("needs_approval.md"))
        self.assertEqual(len(parked), 1, "task should be in Pending_Approval/email/")

        sidecars = list((Path(self.tmp) / "Pending_Approval" / "email").glob("*.context.json"))
        self.assertEqual(len(sidecars), 1)
        data = json.loads(sidecars[0].read_text(encoding="utf-8"))
        self.assertEqual(data["approval"]["request_id"], "req-test-001")
        self.assertIn("$750", data["summary"]) or self.assertIn("approval", data["summary"])

        # Verify it's not yet in Done/
        done_files = list((Path(self.tmp) / "Done").rglob("*.md"))
        self.assertEqual(done_files, [])

        # Now simulate the human approving the request
        with patch.object(self.queue.approval_handler, "_check_approval", return_value="approved"):
            # On resume, the brain should NOT request approval again
            self.brain.queue_response(summary="Completed the payment.", approval_info=None)
            handled = self.queue.tick(domain="email")

        # Task should have been resumed (back to Needs_Action, then claimed+processed+done)
        self.assertGreaterEqual(handled, 1, "resume scan should re-queue the task")

        done = list((Path(self.tmp) / "Done" / "email").glob("*.md"))
        self.assertEqual(len(done), 1, "task should now be in Done/email/")
        body = done[0].read_text(encoding="utf-8")
        self.assertIn("Resume Marker", body)
        self.assertIn("APPROVED", body.upper())

        # Sidecar should be gone
        sidecars = list((Path(self.tmp) / "Pending_Approval" / "email").glob("*.context.json"))
        self.assertEqual(sidecars, [])

    def test_park_then_resume_rejected(self):
        self.brain.queue_response(
            summary="Awaiting approval.",
            approval_info={"request_id": "req-test-002", "action": "send_email"},
        )
        with patch.object(self.handler, "_check_approval", return_value="pending"):
            self.queue.tick(domain="email")

        # Human rejects
        with patch.object(self.queue.approval_handler, "_check_approval", return_value="rejected"):
            self.brain.queue_response(summary="Closed task — rejected.", approval_info=None)
            self.queue.tick(domain="email")

        done = list((Path(self.tmp) / "Done" / "email").glob("*.md"))
        self.assertEqual(len(done), 1)
        body = done[0].read_text(encoding="utf-8")
        self.assertIn("REJECTED", body.upper())


if __name__ == "__main__":
    unittest.main(verbosity=2)
