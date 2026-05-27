"""
Tests for Platinum Tier - Draft Mode
Tests that email/social/Odoo skills create files instead of executing on cloud.
"""

import os
import sys
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(os.path.join(os.path.dirname(__file__), '..')))


class TestDraftMode(unittest.TestCase):
    """Test that action skills create draft files when running as cloud agent."""

    def setUp(self):
        """Set up temp vault and cloud mode."""
        self.test_dir = tempfile.mkdtemp(prefix="test_draft_")
        self.env_patcher = patch.dict(os.environ, {
            'VAULT_PATH': self.test_dir,
            'AGENT_ROLE': 'cloud',
            'AGENT_ID': 'test-cloud-1',
        })
        self.env_patcher.start()

        # Reload agent_config to pick up cloud role
        import importlib
        import agent_config
        importlib.reload(agent_config)

    def tearDown(self):
        self.env_patcher.stop()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_email_send_creates_draft_on_cloud(self):
        """Email send should create a draft file when running as cloud."""
        from skills.action.email_mcp_action import EmailMCPActionSkill
        skill = EmailMCPActionSkill()

        result = skill._send_email(
            to="test@example.com",
            subject="Test Subject",
            body="Test body content"
        )

        self.assertTrue(result.get("success"))
        self.assertEqual(result.get("action"), "draft_file")
        self.assertEqual(result.get("status"), "pending_approval")

        # Verify file was created
        filepath = result.get("filepath")
        self.assertTrue(os.path.exists(filepath))
        content = Path(filepath).read_text()
        self.assertIn("test@example.com", content)
        self.assertIn("Test Subject", content)

    def test_facebook_post_creates_draft_on_cloud(self):
        """Facebook post should create a draft file when running as cloud."""
        from skills.action.facebook_mcp_action import FacebookMCPActionSkill
        skill = FacebookMCPActionSkill()

        result = skill._create_post("Hello Facebook from cloud!")

        self.assertTrue(result.get("success"))
        self.assertEqual(result.get("action"), "draft_file")

        filepath = result.get("filepath")
        self.assertTrue(os.path.exists(filepath))
        content = Path(filepath).read_text()
        self.assertIn("Hello Facebook from cloud!", content)
        self.assertIn("platform: facebook", content)

    def test_twitter_tweet_creates_draft_on_cloud(self):
        """Tweet should create a draft file when running as cloud."""
        from skills.action.twitter_mcp_action import TwitterMCPActionSkill
        skill = TwitterMCPActionSkill()

        result = skill._create_tweet("Cloud tweet test!")

        self.assertTrue(result.get("success"))
        self.assertEqual(result.get("action"), "draft_file")

        filepath = result.get("filepath")
        self.assertTrue(os.path.exists(filepath))
        content = Path(filepath).read_text()
        self.assertIn("Cloud tweet test!", content)
        self.assertIn("platform: twitter", content)

    def test_linkedin_post_creates_draft_on_cloud(self):
        """LinkedIn post should create a draft file when running as cloud."""
        from skills.action.linkedin_mcp_action import LinkedInMCPActionSkill
        skill = LinkedInMCPActionSkill()

        result = skill._create_post("LinkedIn cloud draft")

        self.assertTrue(result.get("success"))
        self.assertEqual(result.get("action"), "draft_file")

        filepath = result.get("filepath")
        self.assertTrue(os.path.exists(filepath))
        content = Path(filepath).read_text()
        self.assertIn("LinkedIn cloud draft", content)
        self.assertIn("platform: linkedin", content)

    def test_odoo_confirm_invoice_creates_draft_on_cloud(self):
        """Odoo confirm_invoice should create a draft on cloud."""
        from skills.action.odoo_mcp_action import OdooMCPActionSkill
        skill = OdooMCPActionSkill()

        result = skill._confirm_invoice(invoice_id=42)

        self.assertTrue(result.get("success"))
        self.assertEqual(result.get("action"), "draft_file")

        filepath = result.get("filepath")
        self.assertTrue(os.path.exists(filepath))
        content = Path(filepath).read_text()
        self.assertIn("confirm_invoice", content)
        self.assertIn("42", content)

    def test_odoo_register_payment_creates_draft_on_cloud(self):
        """Odoo register_payment should create a draft on cloud."""
        from skills.action.odoo_mcp_action import OdooMCPActionSkill
        skill = OdooMCPActionSkill()

        result = skill._register_payment(invoice_id=42, amount=100.50)

        self.assertTrue(result.get("success"))
        self.assertEqual(result.get("action"), "draft_file")

        filepath = result.get("filepath")
        self.assertTrue(os.path.exists(filepath))
        content = Path(filepath).read_text()
        self.assertIn("register_payment", content)
        self.assertIn("100.5", content)

    def test_email_send_calls_mcp_on_local(self):
        """Email send should call MCP server when running as local."""
        # Switch to local mode
        with patch.dict(os.environ, {'AGENT_ROLE': 'local'}):
            import importlib
            import agent_config
            importlib.reload(agent_config)

            from skills.action.email_mcp_action import EmailMCPActionSkill
            skill = EmailMCPActionSkill()

            # Mock the MCP call
            with patch.object(skill, '_call_mcp', return_value={"success": True, "message": "Sent"}):
                result = skill._send_email(
                    to="test@example.com",
                    subject="Test",
                    body="Body"
                )
                self.assertTrue(result.get("success"))
                self.assertEqual(result.get("action"), "send")

    def test_draft_files_go_to_correct_directories(self):
        """Draft files should be created in domain-specific Pending_Approval/ subdirs."""
        from skills.action.email_mcp_action import EmailMCPActionSkill
        from skills.action.facebook_mcp_action import FacebookMCPActionSkill

        email_skill = EmailMCPActionSkill()
        fb_skill = FacebookMCPActionSkill()

        email_result = email_skill._send_email("a@b.com", "Subj", "Body")
        fb_result = fb_skill._create_post("Hello!")

        email_path = email_result.get("filepath")
        fb_path = fb_result.get("filepath")

        self.assertIn("email", email_path)
        self.assertIn("social", fb_path)

    def test_instagram_post_creates_draft_on_cloud(self):
        """Instagram post should create a draft file when running as cloud."""
        from skills.action.facebook_mcp_action import FacebookMCPActionSkill
        skill = FacebookMCPActionSkill()

        result = skill._create_instagram_post(
            caption="IG caption",
            image_url="https://example.com/image.jpg"
        )

        self.assertTrue(result.get("success"))
        self.assertEqual(result.get("action"), "draft_file")

        filepath = result.get("filepath")
        content = Path(filepath).read_text()
        self.assertIn("IG caption", content)
        self.assertIn("instagram", content)

    def test_draft_file_contains_agent_id(self):
        """Draft files should contain the creating agent's ID."""
        from skills.action.email_mcp_action import EmailMCPActionSkill
        skill = EmailMCPActionSkill()

        result = skill._send_email("a@b.com", "Subj", "Body")
        content = Path(result["filepath"]).read_text()
        self.assertIn("test-cloud-1", content)


if __name__ == '__main__':
    unittest.main()
