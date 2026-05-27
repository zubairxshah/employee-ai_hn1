"""
Tests for Platinum Tier - End-to-End Demo Flow
Tests the full pipeline: email → cloud draft → local approve → send → Done
"""

import os
import sys
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

sys.path.insert(0, str(os.path.join(os.path.dirname(__file__), '..')))


class TestPlatinumDemoFlow(unittest.TestCase):
    """Test the full Platinum tier end-to-end flow."""

    def setUp(self):
        """Create temporary vault with full directory structure."""
        self.test_dir = tempfile.mkdtemp(prefix="test_demo_")

        # Create full vault structure
        dirs = [
            "Inbox", "Needs_Action/email", "Needs_Action/social",
            "Needs_Action/accounting", "In_Progress",
            "Pending_Approval/email", "Pending_Approval/social",
            "Pending_Approval/accounting",
            "Approved/email", "Approved/social", "Approved/accounting",
            "Done/email", "Done/social", "Done/accounting",
            "Updates", "Signals", "Logs",
        ]
        for d in dirs:
            os.makedirs(os.path.join(self.test_dir, d), exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_full_email_flow(self):
        """
        Full flow: email task → cloud creates draft → local approves → send → Done
        """
        # Step 1: Create an email task in Needs_Action/email/
        task_path = Path(self.test_dir) / "Needs_Action" / "email" / "TASK_email_001.md"
        task_path.write_text("""---
to: client@example.com
subject: Invoice #123
---

Dear Client,
Please find your invoice attached.
Best regards
""", encoding="utf-8")

        # Step 2: Cloud agent claims the task
        with patch.dict(os.environ, {
            'VAULT_PATH': self.test_dir,
            'AGENT_ROLE': 'cloud',
            'AGENT_ID': 'cloud-test',
        }):
            import importlib
            import agent_config
            importlib.reload(agent_config)

            from claim_manager import ClaimManager
            cloud_claim = ClaimManager(vault_path=self.test_dir)
            claimed = cloud_claim.claim(task_path)

            self.assertIsNotNone(claimed, "Cloud should claim the task")
            self.assertFalse(task_path.exists(), "Original task should be gone")

        # Step 3: Cloud creates a draft in Pending_Approval/email/
        draft_path = Path(self.test_dir) / "Pending_Approval" / "email" / "EMAIL_DRAFT_test.md"
        draft_path.write_text("""---
type: send_email
action: send_email
to: client@example.com
subject: Invoice #123
created_by: cloud-test
status: pending_approval
---

## Email Draft

**To:** client@example.com
**Subject:** Invoice #123

### Body
Dear Client,
Please find your invoice attached.
Best regards
""", encoding="utf-8")

        self.assertTrue(draft_path.exists(), "Draft should exist in Pending_Approval")

        # Step 4: Simulate human approval (move to Approved/)
        approved_path = Path(self.test_dir) / "Approved" / "email" / "EMAIL_DRAFT_test.md"
        os.rename(str(draft_path), str(approved_path))

        self.assertTrue(approved_path.exists(), "Draft should be in Approved/")
        self.assertFalse(draft_path.exists(), "Draft should be gone from Pending")

        # Step 5: Local agent picks up and "executes" (mock the MCP call)
        with patch.dict(os.environ, {
            'VAULT_PATH': self.test_dir,
            'AGENT_ROLE': 'local',
            'AGENT_ID': 'local-test',
        }):
            import importlib
            import agent_config
            importlib.reload(agent_config)

            # Verify local can execute send_email
            self.assertTrue(agent_config.can_execute_action('send_email'))

            # Move to Done (simulating what local_orchestrator does)
            done_path = Path(self.test_dir) / "Done" / "email" / "EMAIL_DRAFT_test.md"
            os.rename(str(approved_path), str(done_path))

            self.assertTrue(done_path.exists(), "File should be in Done/")
            self.assertFalse(approved_path.exists())

    def test_full_social_flow(self):
        """Social task → cloud draft → local approve → post → Done"""
        # Step 1: Social task
        task_path = Path(self.test_dir) / "Needs_Action" / "social" / "TASK_social_001.md"
        task_path.write_text("""---
platform: facebook
---

Exciting news! Our new product is launching today!
""", encoding="utf-8")

        # Step 2: Cloud claims
        with patch.dict(os.environ, {
            'VAULT_PATH': self.test_dir,
            'AGENT_ROLE': 'cloud',
            'AGENT_ID': 'cloud-test',
        }):
            import importlib
            import agent_config
            importlib.reload(agent_config)

            from claim_manager import ClaimManager
            mgr = ClaimManager(vault_path=self.test_dir)
            claimed = mgr.claim(task_path)
            self.assertIsNotNone(claimed)

            # Cloud cannot create_post directly
            self.assertFalse(agent_config.can_execute_action('create_post'))

        # Step 3: Draft created
        draft_path = Path(self.test_dir) / "Pending_Approval" / "social" / "SOCIAL_DRAFT_fb.md"
        draft_path.write_text("""---
type: social_post
action: create_post
platform: facebook
status: pending_approval
---

Exciting news! Our new product is launching today!
""", encoding="utf-8")

        # Step 4: Approve
        approved_path = Path(self.test_dir) / "Approved" / "social" / "SOCIAL_DRAFT_fb.md"
        os.rename(str(draft_path), str(approved_path))

        # Step 5: Local executes
        with patch.dict(os.environ, {'AGENT_ROLE': 'local'}):
            import importlib
            import agent_config
            importlib.reload(agent_config)
            self.assertTrue(agent_config.can_execute_action('create_post'))

            done_path = Path(self.test_dir) / "Done" / "social" / "SOCIAL_DRAFT_fb.md"
            os.rename(str(approved_path), str(done_path))
            self.assertTrue(done_path.exists())

    def test_dashboard_update_flow(self):
        """Cloud writes updates, local merges into Dashboard."""
        with patch.dict(os.environ, {
            'VAULT_PATH': self.test_dir,
            'AGENT_ROLE': 'cloud',
            'AGENT_ID': 'cloud-test',
        }):
            import importlib
            import agent_config
            importlib.reload(agent_config)

            from dashboard_manager import DashboardManager
            dashboard = DashboardManager(vault_path=self.test_dir)

            # Cloud writes update
            dashboard.write_update("email_draft", {
                "summary": "Created draft for client@example.com"
            })

        # Local merges
        with patch.dict(os.environ, {'AGENT_ROLE': 'local'}):
            import importlib
            import agent_config
            importlib.reload(agent_config)

            dashboard = DashboardManager(vault_path=self.test_dir)
            merged = dashboard.merge_updates_into_dashboard()
            self.assertEqual(merged, 1)

            # Check Dashboard.md was created
            dashboard_path = Path(self.test_dir) / "Dashboard.md"
            self.assertTrue(dashboard_path.exists())
            content = dashboard_path.read_text()
            self.assertIn("client@example.com", content)

    def test_signal_flow(self):
        """Cloud writes signal, local reads it."""
        with patch.dict(os.environ, {
            'VAULT_PATH': self.test_dir,
            'AGENT_ROLE': 'cloud',
            'AGENT_ID': 'cloud-test',
        }):
            from dashboard_manager import DashboardManager
            dashboard = DashboardManager(vault_path=self.test_dir)
            dashboard.write_signal("new_draft_ready", {"domain": "email", "filename": "test.md"})

        # Local reads signal
        dashboard = DashboardManager(vault_path=self.test_dir)
        signals = dashboard.read_signals()
        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0]["signal"], "new_draft_ready")

        # Signals should be consumed (deleted)
        signals2 = dashboard.read_signals()
        self.assertEqual(len(signals2), 0)

    def test_cloud_safety_validation(self):
        """Cloud agent should fail safety check if sensitive creds present."""
        with patch.dict(os.environ, {
            'AGENT_ROLE': 'cloud',
            'WHATSAPP_NOTIFICATION_PHONE': '+1234567890',
        }):
            import importlib
            import agent_config
            importlib.reload(agent_config)

            from security_config import SecurityConfig
            config = SecurityConfig()
            self.assertFalse(config.validate_cloud_safety())

    def test_cloud_safety_passes_without_sensitive_creds(self):
        """Cloud agent should pass safety check without sensitive creds."""
        with patch.dict(os.environ, {
            'AGENT_ROLE': 'cloud',
        }, clear=False):
            # Remove sensitive creds
            for key in ['GMAIL_APP_PASSWORD', 'WHATSAPP_NOTIFICATION_PHONE',
                        'BANK_API_TOKEN', 'WHATSAPP_SESSION_PATH']:
                os.environ.pop(key, None)

            import importlib
            import agent_config
            importlib.reload(agent_config)

            from security_config import SecurityConfig
            config = SecurityConfig()
            self.assertTrue(config.validate_cloud_safety())


if __name__ == '__main__':
    unittest.main()
