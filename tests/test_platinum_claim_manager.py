"""
Tests for Platinum Tier - Claim Manager
Tests atomic claim, race conditions, release, and is_claimed.
"""

import os
import sys
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(os.path.join(os.path.dirname(__file__), '..')))


class TestClaimManager(unittest.TestCase):
    """Test claim-by-move protocol."""

    def setUp(self):
        """Create a temporary vault structure for testing."""
        self.test_dir = tempfile.mkdtemp(prefix="test_vault_")
        self.vault_path = self.test_dir

        # Create vault structure
        for subdir in ["Needs_Action/email", "Needs_Action/social",
                        "In_Progress", "Done", "Pending_Approval"]:
            os.makedirs(os.path.join(self.vault_path, subdir), exist_ok=True)

        # Patch environment
        self.env_patcher = patch.dict(os.environ, {
            'VAULT_PATH': self.vault_path,
            'AGENT_ROLE': 'cloud',
            'AGENT_ID': 'test-agent-1',
        })
        self.env_patcher.start()

        # Reload modules
        import importlib
        import agent_config
        importlib.reload(agent_config)

        from claim_manager import ClaimManager
        self.mgr = ClaimManager(vault_path=self.vault_path)

    def tearDown(self):
        self.env_patcher.stop()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _create_task(self, domain: str, name: str, content: str = "test") -> Path:
        """Helper to create a task file."""
        filepath = Path(self.vault_path) / "Needs_Action" / domain / name
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(content, encoding="utf-8")
        return filepath

    def test_list_available_empty(self):
        """list_available() should return empty list when no tasks."""
        result = self.mgr.list_available(domain="email")
        self.assertEqual(result, [])

    def test_list_available_with_tasks(self):
        """list_available() should return task files."""
        self._create_task("email", "task1.md")
        self._create_task("email", "task2.md")
        result = self.mgr.list_available(domain="email")
        self.assertEqual(len(result), 2)

    def test_claim_moves_file(self):
        """claim() should move file from Needs_Action to In_Progress/agent_id."""
        task = self._create_task("email", "task1.md", "email content")
        claimed = self.mgr.claim(task)

        self.assertIsNotNone(claimed)
        self.assertFalse(task.exists())  # Original gone
        self.assertTrue(claimed.exists())  # New location exists
        self.assertEqual(claimed.read_text(), "email content")

    def test_claim_nonexistent_file(self):
        """claim() should return None for non-existent file."""
        fake_path = Path(self.vault_path) / "Needs_Action" / "email" / "nonexistent.md"
        result = self.mgr.claim(fake_path)
        self.assertIsNone(result)

    def test_claim_already_claimed(self):
        """Second claim on same file should fail."""
        task = self._create_task("email", "task1.md")
        claimed = self.mgr.claim(task)
        self.assertIsNotNone(claimed)

        # Try claiming same path again (file is gone)
        result = self.mgr.claim(task)
        self.assertIsNone(result)

    def test_release_done(self):
        """release_done() should move file to Done/."""
        task = self._create_task("email", "task1.md", "content")
        claimed = self.mgr.claim(task)
        done = self.mgr.release_done(claimed, domain="email")

        self.assertIsNotNone(done)
        self.assertFalse(claimed.exists())
        self.assertTrue(done.exists())
        self.assertIn("Done", str(done))

    def test_release_pending_approval(self):
        """release_pending_approval() should move to Pending_Approval/."""
        task = self._create_task("email", "task1.md", "draft content")
        claimed = self.mgr.claim(task)
        pending = self.mgr.release_pending_approval(claimed, domain="email")

        self.assertIsNotNone(pending)
        self.assertFalse(claimed.exists())
        self.assertTrue(pending.exists())
        self.assertIn("Pending_Approval", str(pending))

    def test_release_back(self):
        """release_back() should return file to Needs_Action/."""
        task = self._create_task("email", "task1.md", "content")
        claimed = self.mgr.claim(task)
        released = self.mgr.release_back(claimed, domain="email")

        self.assertIsNotNone(released)
        self.assertFalse(claimed.exists())
        self.assertTrue(released.exists())
        self.assertIn("Needs_Action", str(released))

    def test_is_claimed_true(self):
        """is_claimed() should return True for claimed files."""
        task = self._create_task("email", "task1.md")
        self.mgr.claim(task)
        self.assertTrue(self.mgr.is_claimed("task1.md"))

    def test_is_claimed_false(self):
        """is_claimed() should return False for unclaimed files."""
        self.assertFalse(self.mgr.is_claimed("nonexistent.md"))

    def test_get_my_claims(self):
        """get_my_claims() should list all files claimed by this agent."""
        self._create_task("email", "task1.md")
        self._create_task("email", "task2.md")
        tasks = self.mgr.list_available(domain="email")

        for t in tasks:
            self.mgr.claim(t)

        claims = self.mgr.get_my_claims()
        self.assertEqual(len(claims), 2)

    def test_name_collision_handling(self):
        """Claiming two files with the same name should not overwrite."""
        task1 = self._create_task("email", "task.md", "first")
        claimed1 = self.mgr.claim(task1)

        task2 = self._create_task("social", "task.md", "second")
        claimed2 = self.mgr.claim(task2)

        self.assertIsNotNone(claimed1)
        self.assertIsNotNone(claimed2)
        self.assertNotEqual(str(claimed1), str(claimed2))


if __name__ == '__main__':
    unittest.main()
