"""
Tests for Platinum Tier - Agent Configuration
Tests role detection, can_execute_action(), and domain ownership.
"""

import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(os.path.join(os.path.dirname(__file__), '..')))


class TestAgentConfig(unittest.TestCase):
    """Test agent configuration and role-based gating."""

    def test_default_role_is_local(self):
        """Default agent role should be 'local'."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('AGENT_ROLE', None)
            # Re-import to pick up env change
            import importlib
            import agent_config
            importlib.reload(agent_config)
            self.assertEqual(agent_config.AGENT_ROLE, "local")

    def test_cloud_role_from_env(self):
        """AGENT_ROLE=cloud should set cloud role."""
        with patch.dict(os.environ, {'AGENT_ROLE': 'cloud'}):
            import importlib
            import agent_config
            importlib.reload(agent_config)
            self.assertTrue(agent_config.is_cloud())
            self.assertFalse(agent_config.is_local())

    def test_local_role_from_env(self):
        """AGENT_ROLE=local should set local role."""
        with patch.dict(os.environ, {'AGENT_ROLE': 'local'}):
            import importlib
            import agent_config
            importlib.reload(agent_config)
            self.assertTrue(agent_config.is_local())
            self.assertFalse(agent_config.is_cloud())

    def test_cloud_blocks_send_email(self):
        """Cloud agent should not be able to execute send_email."""
        with patch.dict(os.environ, {'AGENT_ROLE': 'cloud'}):
            import importlib
            import agent_config
            importlib.reload(agent_config)
            self.assertFalse(agent_config.can_execute_action('send_email'))

    def test_cloud_blocks_create_post(self):
        """Cloud agent should not be able to execute create_post."""
        with patch.dict(os.environ, {'AGENT_ROLE': 'cloud'}):
            import importlib
            import agent_config
            importlib.reload(agent_config)
            self.assertFalse(agent_config.can_execute_action('create_post'))

    def test_cloud_blocks_create_tweet(self):
        """Cloud agent should not be able to execute create_tweet."""
        with patch.dict(os.environ, {'AGENT_ROLE': 'cloud'}):
            import importlib
            import agent_config
            importlib.reload(agent_config)
            self.assertFalse(agent_config.can_execute_action('create_tweet'))

    def test_cloud_blocks_confirm_invoice(self):
        """Cloud agent should not be able to confirm invoices."""
        with patch.dict(os.environ, {'AGENT_ROLE': 'cloud'}):
            import importlib
            import agent_config
            importlib.reload(agent_config)
            self.assertFalse(agent_config.can_execute_action('confirm_invoice'))

    def test_cloud_blocks_register_payment(self):
        """Cloud agent should not be able to register payments."""
        with patch.dict(os.environ, {'AGENT_ROLE': 'cloud'}):
            import importlib
            import agent_config
            importlib.reload(agent_config)
            self.assertFalse(agent_config.can_execute_action('register_payment'))

    def test_cloud_allows_draft(self):
        """Cloud agent should be able to create drafts."""
        with patch.dict(os.environ, {'AGENT_ROLE': 'cloud'}):
            import importlib
            import agent_config
            importlib.reload(agent_config)
            self.assertTrue(agent_config.can_execute_action('draft'))
            self.assertTrue(agent_config.can_execute_action('create_draft'))

    def test_cloud_allows_read_operations(self):
        """Cloud agent should be able to read Odoo data."""
        with patch.dict(os.environ, {'AGENT_ROLE': 'cloud'}):
            import importlib
            import agent_config
            importlib.reload(agent_config)
            self.assertTrue(agent_config.can_execute_action('get_invoices'))
            self.assertTrue(agent_config.can_execute_action('get_customers'))
            self.assertTrue(agent_config.can_execute_action('get_financial_summary'))

    def test_local_allows_everything(self):
        """Local agent should be able to execute all actions."""
        with patch.dict(os.environ, {'AGENT_ROLE': 'local'}):
            import importlib
            import agent_config
            importlib.reload(agent_config)
            self.assertTrue(agent_config.can_execute_action('send_email'))
            self.assertTrue(agent_config.can_execute_action('create_post'))
            self.assertTrue(agent_config.can_execute_action('confirm_invoice'))
            self.assertTrue(agent_config.can_execute_action('register_payment'))

    def test_domain_ownership(self):
        """Domain ownership should be correctly mapped."""
        import agent_config
        self.assertEqual(agent_config.get_domain_owner('email_triage'), 'cloud')
        self.assertEqual(agent_config.get_domain_owner('social_drafts'), 'cloud')
        self.assertEqual(agent_config.get_domain_owner('approvals'), 'local')
        self.assertEqual(agent_config.get_domain_owner('whatsapp'), 'local')
        self.assertEqual(agent_config.get_domain_owner('payments'), 'local')

    def test_unknown_domain_defaults_to_local(self):
        """Unknown domains should default to local for safety."""
        import agent_config
        self.assertEqual(agent_config.get_domain_owner('unknown_domain'), 'local')

    def test_vault_path_from_env(self):
        """get_vault_path() should read from VAULT_PATH env var."""
        with patch.dict(os.environ, {'VAULT_PATH': '/test/vault'}):
            import importlib
            import agent_config
            importlib.reload(agent_config)
            self.assertEqual(agent_config.get_vault_path(), '/test/vault')


if __name__ == '__main__':
    unittest.main()
