"""
Tests for Twitter (X) MCP Server
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
if 'security_config' not in sys.modules:
    sys.modules['security_config'] = MagicMock()
    sys.modules['secure_action_executor'] = MagicMock()

    mock_security = MagicMock()
    mock_security.sanitize_input = lambda x: x
    mock_security.log_action = MagicMock()
    mock_security.logger = MagicMock()
    sys.modules['security_config'].get_security_config = MagicMock(return_value=mock_security)
    sys.modules['secure_action_executor'].get_secure_executor = MagicMock(return_value=MagicMock())

from mcp_servers.twitter_mcp import app, create_draft_tweet, generate_pkce


class TestTwitterMCPEndpoints(unittest.TestCase):
    """Test Twitter MCP Flask endpoints"""

    def setUp(self):
        self.client = app.test_client()
        app.config['TESTING'] = True

    def test_capabilities(self):
        response = self.client.get('/capabilities')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['name'], 'twitter-mcp')
        self.assertEqual(data['max_tweet_length'], 280)
        self.assertIn('operations', data)

    def test_health(self):
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'healthy')
        self.assertEqual(data['service'], 'twitter-mcp')

    def test_get_auth_url_no_config(self):
        with patch('mcp_servers.twitter_mcp.load_twitter_config',
                   return_value={'client_id': '', 'client_secret': '',
                                 'redirect_uri': ''}):
            response = self.client.get('/get_auth_url')
            self.assertEqual(response.status_code, 400)

    def test_get_auth_url_configured(self):
        with patch('mcp_servers.twitter_mcp.load_twitter_config',
                   return_value={'client_id': 'test123', 'client_secret': 'secret',
                                 'redirect_uri': 'http://localhost:8007/callback'}):
            response = self.client.get('/get_auth_url')
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertTrue(data['success'])
            self.assertIn('authorization_url', data)

    def test_create_tweet_missing_text(self):
        response = self.client.post('/create_tweet',
                                    json={},
                                    content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_create_tweet_too_long(self):
        response = self.client.post('/create_tweet',
                                    json={"text": "x" * 281},
                                    content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_create_draft(self):
        with patch('mcp_servers.twitter_mcp.VAULT_PATH',
                   str(Path(__file__).parent / 'test_vault_tw')):
            response = self.client.post('/create_draft',
                                        json={"text": "Test tweet draft"},
                                        content_type='application/json')
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertTrue(data['success'])

            # Clean up
            import shutil
            test_vault = Path(__file__).parent / 'test_vault_tw'
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


class TestPKCE(unittest.TestCase):
    """Test PKCE generation"""

    def test_generate_pkce(self):
        verifier, challenge, state = generate_pkce()
        self.assertTrue(len(verifier) > 40)
        self.assertTrue(len(challenge) > 20)
        self.assertTrue(len(state) > 20)

    def test_pkce_uniqueness(self):
        v1, c1, s1 = generate_pkce()
        v2, c2, s2 = generate_pkce()
        self.assertNotEqual(v1, v2)
        self.assertNotEqual(s1, s2)


class TestDraftCreation(unittest.TestCase):
    """Test draft tweet creation logic"""

    def setUp(self):
        self.test_vault = str(Path(__file__).parent / 'test_vault_tw_draft')

    def tearDown(self):
        import shutil
        if os.path.exists(self.test_vault):
            shutil.rmtree(self.test_vault)

    def test_create_draft_tweet(self):
        with patch('mcp_servers.twitter_mcp.VAULT_PATH', self.test_vault):
            result = create_draft_tweet("Hello from Twitter!")
            self.assertTrue(result['success'])
            self.assertIn('filepath', result)
            self.assertEqual(result['char_count'], 19)
            self.assertTrue(os.path.exists(result['filepath']))


if __name__ == '__main__':
    unittest.main()
