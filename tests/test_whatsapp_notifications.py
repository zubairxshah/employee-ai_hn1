"""
Tests for WhatsApp Notification Service
"""

import os
import sys
import json
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from whatsapp_notifications import WhatsAppNotificationService


class TestWhatsAppNotificationService(unittest.TestCase):
    """Test WhatsAppNotificationService"""

    def setUp(self):
        self.test_vault = str(Path(__file__).parent / 'test_vault_wa')
        Path(self.test_vault, 'Logs').mkdir(parents=True, exist_ok=True)
        Path(self.test_vault, 'Pending_Approval').mkdir(parents=True, exist_ok=True)

        # Patch the state file and vault path
        self.state_patcher = patch('whatsapp_notifications.STATE_FILE',
                                   os.path.join(self.test_vault, 'Logs', 'notification_state.json'))
        self.vault_patcher = patch('whatsapp_notifications.VAULT_PATH', self.test_vault)
        self.state_patcher.start()
        self.vault_patcher.start()

        self.service = WhatsAppNotificationService(
            poll_interval=60,
            cooldown_hours=1,
            phone='+1234567890'
        )

    def tearDown(self):
        self.state_patcher.stop()
        self.vault_patcher.stop()
        import shutil
        if os.path.exists(self.test_vault):
            shutil.rmtree(self.test_vault)

    def test_init(self):
        self.assertEqual(self.service.poll_interval, 60)
        self.assertEqual(self.service.cooldown_hours, 1)
        self.assertEqual(self.service.phone, '+1234567890')

    def test_state_persistence(self):
        self.service._mark_notified('TEST-001', 'invoices')
        self.assertTrue(self.service._is_in_cooldown('TEST-001', 'invoices'))
        self.assertFalse(self.service._is_in_cooldown('TEST-002', 'invoices'))

    def test_cooldown_expired(self):
        # Manually set a past notification
        self.service.state['notified_invoices'] = {
            'OLD-001': (datetime.now() - timedelta(hours=2)).isoformat()
        }
        self.assertFalse(self.service._is_in_cooldown('OLD-001', 'invoices'))

    def test_cooldown_active(self):
        self.service.state['notified_invoices'] = {
            'RECENT-001': datetime.now().isoformat()
        }
        self.assertTrue(self.service._is_in_cooldown('RECENT-001', 'invoices'))

    @patch('whatsapp_notifications.WHATSAPP_MCP')
    def test_send_whatsapp(self, mock_wa):
        mock_wa.post.return_value = {"success": True}
        result = self.service._send_whatsapp("Test message")
        self.assertTrue(result)
        mock_wa.post.assert_called_once()

    @patch('whatsapp_notifications.WHATSAPP_MCP')
    def test_send_whatsapp_failure(self, mock_wa):
        mock_wa.post.return_value = {"success": False, "error": "timeout"}
        result = self.service._send_whatsapp("Test message")
        self.assertFalse(result)

    @patch('whatsapp_notifications.WHATSAPP_MCP')
    @patch('whatsapp_notifications.ODOO_MCP')
    def test_check_payment_reminders_no_overdue(self, mock_odoo, mock_wa):
        mock_odoo.post.return_value = {"success": True, "invoices": []}
        sent = self.service.check_and_send_payment_reminders()
        self.assertEqual(sent, 0)

    @patch('whatsapp_notifications.WHATSAPP_MCP')
    @patch('whatsapp_notifications.ODOO_MCP')
    def test_check_payment_reminders_with_overdue(self, mock_odoo, mock_wa):
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        mock_odoo.post.return_value = {
            "success": True,
            "invoices": [{
                "id": 1,
                "name": "INV/2026/0001",
                "partner_name": "Test Customer",
                "amount_total": 500.00,
                "invoice_date_due": yesterday
            }]
        }
        mock_wa.post.return_value = {"success": True}

        sent = self.service.check_and_send_payment_reminders()
        self.assertEqual(sent, 1)

    @patch('whatsapp_notifications.WHATSAPP_MCP')
    def test_check_approval_alerts(self, mock_wa):
        # Create a test pending approval file
        pending_dir = Path(self.test_vault) / "Pending_Approval" / "Test_Drafts"
        pending_dir.mkdir(parents=True, exist_ok=True)
        test_file = pending_dir / "TEST_APPROVAL.md"
        test_file.write_text("---\ntype: test\n---\nTest approval")

        mock_wa.post.return_value = {"success": True}

        sent = self.service.check_and_send_approval_alerts()
        self.assertEqual(sent, 1)

    @patch('whatsapp_notifications.WHATSAPP_MCP')
    @patch('whatsapp_notifications.ODOO_MCP')
    def test_daily_summary(self, mock_odoo, mock_wa):
        mock_odoo.post.return_value = {"success": True, "invoices": []}
        mock_wa.post.return_value = {"success": True}

        result = self.service.send_daily_summary()
        self.assertTrue(result)

    @patch('whatsapp_notifications.WHATSAPP_MCP')
    @patch('whatsapp_notifications.ODOO_MCP')
    def test_daily_summary_not_sent_twice(self, mock_odoo, mock_wa):
        mock_odoo.post.return_value = {"success": True, "invoices": []}
        mock_wa.post.return_value = {"success": True}

        # First call should succeed
        self.service.send_daily_summary()
        # Second call same day should skip
        result = self.service.send_daily_summary()
        self.assertFalse(result)

    @patch('whatsapp_notifications.WHATSAPP_MCP')
    @patch('whatsapp_notifications.ODOO_MCP')
    def test_run_notification_cycle(self, mock_odoo, mock_wa):
        mock_odoo.post.return_value = {"success": True, "invoices": []}
        mock_wa.post.return_value = {"success": True}

        result = self.service.run_notification_cycle()
        self.assertIn('timestamp', result)
        self.assertIn('payment_reminders_sent', result)
        self.assertIn('approval_alerts_sent', result)
        self.assertIn('daily_summary_sent', result)


if __name__ == '__main__':
    unittest.main()
