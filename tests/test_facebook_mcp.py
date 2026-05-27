"""
Tests for Facebook/Instagram MCP Server
"""

import os
import sys
import json
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'mcp_servers'))

# Mock security modules before importing
sys.modules['security_config'] = MagicMock()
sys.modules['secure_action_executor'] = MagicMock()

mock_security = MagicMock()
mock_security.sanitize_input = lambda x: x
mock_security.log_action = MagicMock()
mock_security.logger = MagicMock()
sys.modules['security_config'].get_security_config = MagicMock(return_value=mock_security)
sys.modules['secure_action_executor'].get_secure_executor = MagicMock(return_value=MagicMock())

from mcp_servers.facebook_mcp import app, create_draft_post, get_engagement_summary


class TestFacebookMCPEndpoints(unittest.TestCase):
    """Test Facebook MCP Flask endpoints"""

    def setUp(self):
        self.client = app.test_client()
        app.config['TESTING'] = True

    def test_capabilities(self):
        response = self.client.get('/capabilities')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['name'], 'facebook-mcp')
        self.assertIn('operations', data)

    def test_health(self):
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'healthy')
        self.assertEqual(data['service'], 'facebook-mcp')

    def test_get_auth_url_no_config(self):
        with patch('mcp_servers.facebook_mcp.load_facebook_config',
                   return_value={'app_id': '', 'app_secret': '', 'redirect_uri': ''}):
            response = self.client.get('/get_auth_url')
            self.assertEqual(response.status_code, 400)

    def test_get_auth_url_configured(self):
        with patch('mcp_servers.facebook_mcp.load_facebook_config',
                   return_value={'app_id': 'test123', 'app_secret': 'secret',
                                 'redirect_uri': 'http://localhost:8006/callback'}):
            response = self.client.get('/get_auth_url')
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertTrue(data['success'])
            self.assertIn('authorization_url', data)

    def test_create_post_missing_message(self):
        response = self.client.post('/create_post',
                                    json={},
                                    content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_create_instagram_post_missing_image(self):
        response = self.client.post('/create_instagram_post',
                                    json={"caption": "Test post"},
                                    content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_create_draft(self):
        with patch('mcp_servers.facebook_mcp.VAULT_PATH',
                   str(Path(__file__).parent / 'test_vault_fb')):
            response = self.client.post('/create_draft',
                                        json={"text": "Test draft", "platform": "facebook"},
                                        content_type='application/json')
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertTrue(data['success'])

            # Clean up
            import shutil
            test_vault = Path(__file__).parent / 'test_vault_fb'
            if test_vault.exists():
                shutil.rmtree(test_vault)

    def test_check_draft_not_found(self):
        response = self.client.post('/check_draft_status',
                                    json={"filename": "nonexistent.md"},
                                    content_type='application/json')
        self.assertEqual(response.status_code, 404)

    def test_exchange_token_missing_code(self):
        response = self.client.post('/exchange_token',
                                    json={},
                                    content_type='application/json')
        self.assertEqual(response.status_code, 400)


class TestFacebookDraftCreation(unittest.TestCase):
    """Test draft post creation logic"""

    def setUp(self):
        self.test_vault = str(Path(__file__).parent / 'test_vault_fb_draft')

    def tearDown(self):
        import shutil
        if os.path.exists(self.test_vault):
            shutil.rmtree(self.test_vault)

    @patch('mcp_servers.facebook_mcp.VAULT_PATH')
    def test_create_draft_post(self, mock_vault):
        mock_vault.__str__ = lambda x: self.test_vault
        with patch('mcp_servers.facebook_mcp.VAULT_PATH', self.test_vault):
            result = create_draft_post("Hello World!", platform="facebook")
            self.assertTrue(result['success'])
            self.assertIn('filepath', result)
            self.assertTrue(os.path.exists(result['filepath']))


if __name__ == '__main__':
    unittest.main()
