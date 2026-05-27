"""
Tests for LinkedIn Watcher
"""

import os
import sys
import json
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'watchers' / 'perception'))

from watchers.perception.linkedin_watcher import LinkedInWatcher


class TestLinkedInWatcher(unittest.TestCase):
    """Test LinkedInWatcher"""

    def setUp(self):
        self.test_vault = str(Path(__file__).parent / 'test_vault_li')
        Path(self.test_vault, 'Needs_Action').mkdir(parents=True, exist_ok=True)
        Path(self.test_vault, 'Incoming_LinkedIn').mkdir(parents=True, exist_ok=True)
        Path(self.test_vault, 'Logs').mkdir(parents=True, exist_ok=True)

        self.state_patcher = patch(
            'watchers.perception.linkedin_watcher.STATE_FILE',
            os.path.join(self.test_vault, 'Logs', 'linkedin_watcher_state.json')
        )
        self.state_patcher.start()

        self.watcher = LinkedInWatcher(
            vault_path=self.test_vault,
            check_interval=10
        )

    def tearDown(self):
        self.state_patcher.stop()
        import shutil
        if os.path.exists(self.test_vault):
            shutil.rmtree(self.test_vault)

    def test_init(self):
        self.assertEqual(self.watcher.check_interval, 10)
        self.assertTrue(self.watcher.incoming_dir.exists())

    def test_state_persistence(self):
        self.watcher.processed_ids.add('test-msg-001')
        self.watcher._save_state()

        # Create new watcher instance to test loading
        with patch('watchers.perception.linkedin_watcher.STATE_FILE',
                   os.path.join(self.test_vault, 'Logs', 'linkedin_watcher_state.json')):
            watcher2 = LinkedInWatcher(vault_path=self.test_vault)
            self.assertIn('test-msg-001', watcher2.processed_ids)

    def test_check_vault_no_files(self):
        items = self.watcher._check_vault()
        self.assertEqual(len(items), 0)

    def test_check_vault_with_files(self):
        # Create a test incoming file
        test_file = Path(self.test_vault) / 'Incoming_LinkedIn' / 'test_lead.md'
        test_file.write_text("# Test LinkedIn Lead\nHello, I'm interested.")

        items = self.watcher._check_vault()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['source'], 'vault')
        self.assertEqual(items[0]['filename'], 'test_lead.md')

    def test_check_vault_skips_processed(self):
        # Create a test incoming file
        test_file = Path(self.test_vault) / 'Incoming_LinkedIn' / 'already_done.md'
        test_file.write_text("# Already processed")

        # Mark as processed
        self.watcher.processed_files.add('already_done.md')

        items = self.watcher._check_vault()
        self.assertEqual(len(items), 0)

    @patch('watchers.perception.linkedin_watcher.requests')
    def test_check_api_success(self, mock_requests):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "messages": [
                {"id": "msg-001", "body": "Hello", "from": "John", "created_at": "2026-01-01"}
            ]
        }
        mock_requests.get.return_value = mock_response

        items = self.watcher._check_api()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['id'], 'msg-001')

    @patch('watchers.perception.linkedin_watcher.requests')
    def test_check_api_connection_error(self, mock_requests):
        import requests as req
        mock_requests.ConnectionError = req.ConnectionError
        mock_requests.get.side_effect = req.ConnectionError("refused")

        items = self.watcher._check_api()
        self.assertEqual(len(items), 0)

    @patch('watchers.perception.linkedin_watcher.LinkedInWatcher._trigger_workflow')
    def test_create_action_file_api(self, mock_workflow):
        item = {
            'source': 'api',
            'id': 'msg-002',
            'body': 'Interested in your services',
            'from': 'Jane Smith',
            'created_at': '2026-03-01T10:00:00'
        }

        filepath = self.watcher.create_action_file(item)
        self.assertTrue(filepath.exists())
        self.assertIn('msg-002', self.watcher.processed_ids)

        content = filepath.read_text(encoding='utf-8')
        self.assertIn('linkedin_message', content)
        self.assertIn('Interested in your services', content)

    @patch('watchers.perception.linkedin_watcher.LinkedInWatcher._trigger_workflow')
    def test_create_action_file_vault(self, mock_workflow):
        item = {
            'source': 'vault',
            'id': 'lead_file.md',
            'content': '# LinkedIn Lead\nI want to discuss partnership.',
            'filename': 'lead_file.md',
        }

        filepath = self.watcher.create_action_file(item)
        self.assertTrue(filepath.exists())
        self.assertIn('lead_file.md', self.watcher.processed_files)

    @patch('watchers.perception.linkedin_watcher.LinkedInWatcher._trigger_workflow')
    @patch('watchers.perception.linkedin_watcher.requests')
    def test_check_for_updates_combined(self, mock_requests, mock_workflow):
        # Setup API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "messages": []}
        mock_requests.get.return_value = mock_response

        # Setup vault file
        test_file = Path(self.test_vault) / 'Incoming_LinkedIn' / 'new_lead.md'
        test_file.write_text("# New lead")

        items = self.watcher.check_for_updates()
        self.assertEqual(len(items), 1)  # Only vault item (API returned empty)


if __name__ == '__main__':
    unittest.main()
