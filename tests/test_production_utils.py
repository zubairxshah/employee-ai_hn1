"""
Tests for Production Utilities
"""

import os
import sys
import json
import time
import logging
import unittest
from unittest.mock import patch, MagicMock, PropertyMock
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from production_utils import (
    get_structured_logger,
    mcp_retry,
    register_health_check,
    MCPClient
)


class TestStructuredLogger(unittest.TestCase):
    """Test get_structured_logger()"""

    def setUp(self):
        self.test_log_dir = str(Path(__file__).parent / "test_logs")
        Path(self.test_log_dir).mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        # Close and remove handlers before cleanup to avoid Windows file locks
        for name in list(logging.Logger.manager.loggerDict.keys()):
            if name.startswith('employee.test_'):
                logger = logging.getLogger(name)
                for handler in logger.handlers[:]:
                    handler.close()
                    logger.removeHandler(handler)
                logger.handlers.clear()

        import shutil
        if os.path.exists(self.test_log_dir):
            shutil.rmtree(self.test_log_dir)

    def test_logger_creates_file(self):
        logger = get_structured_logger("test_create", self.test_log_dir)
        logger.info("Test message")
        log_file = os.path.join(self.test_log_dir, "test_create.log")
        self.assertTrue(os.path.exists(log_file))

    def test_logger_json_format(self):
        logger = get_structured_logger("test_json", self.test_log_dir)
        logger.info("Test JSON message")
        log_file = os.path.join(self.test_log_dir, "test_json.log")
        with open(log_file, 'r') as f:
            line = f.readline().strip()
            entry = json.loads(line)
            self.assertEqual(entry['level'], 'INFO')
            self.assertIn('timestamp', entry)
            self.assertEqual(entry['message'], 'Test JSON message')

    def test_logger_no_duplicate_handlers(self):
        logger1 = get_structured_logger("test_nodup", self.test_log_dir)
        logger2 = get_structured_logger("test_nodup", self.test_log_dir)
        self.assertIs(logger1, logger2)


class TestMCPRetry(unittest.TestCase):
    """Test mcp_retry() decorator"""

    @patch('production_utils.time.sleep')
    def test_retry_on_connection_error(self, mock_sleep):
        import requests

        call_count = 0

        @mcp_retry(max_attempts=3, base_delay=0.01)
        def flaky_request():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise requests.ConnectionError("Connection refused")
            return MagicMock(status_code=200)

        result = flaky_request()
        self.assertEqual(call_count, 3)
        self.assertEqual(result.status_code, 200)

    @patch('production_utils.time.sleep')
    def test_no_retry_on_client_error(self, mock_sleep):
        import requests

        @mcp_retry(max_attempts=3, base_delay=0.01)
        def bad_request():
            response = MagicMock()
            response.status_code = 400
            err = requests.HTTPError(response=response)
            raise err

        with self.assertRaises(requests.HTTPError):
            bad_request()

    def test_success_no_retry(self):
        call_count = 0

        @mcp_retry(max_attempts=3)
        def good_request():
            nonlocal call_count
            call_count += 1
            return MagicMock(status_code=200)

        result = good_request()
        self.assertEqual(call_count, 1)


class TestHealthCheck(unittest.TestCase):
    """Test register_health_check()"""

    def test_health_endpoint(self):
        from flask import Flask
        app = Flask(__name__)
        register_health_check(app, "test-service")

        with app.test_client() as client:
            response = client.get('/health')
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertEqual(data['status'], 'healthy')
            self.assertEqual(data['service'], 'test-service')
            self.assertIn('timestamp', data)


class TestMCPClient(unittest.TestCase):
    """Test MCPClient class"""

    @patch('production_utils.requests.request')
    def test_get_success(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "data": "test"}
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response

        client = MCPClient("http://localhost:9999", "test")
        result = client.get("capabilities")

        self.assertTrue(result['success'])
        mock_request.assert_called_once()

    @patch('production_utils.requests.request')
    def test_post_success(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response

        client = MCPClient("http://localhost:9999", "test")
        result = client.post("create_post", {"text": "Hello"})

        self.assertTrue(result['success'])

    @patch('production_utils.requests.request')
    def test_get_failure(self, mock_request):
        import requests
        mock_request.side_effect = requests.ConnectionError("refused")

        client = MCPClient("http://localhost:9999", "test", max_retries=1)
        result = client.get("health")

        self.assertFalse(result['success'])
        self.assertIn('error', result)


if __name__ == '__main__':
    unittest.main()
