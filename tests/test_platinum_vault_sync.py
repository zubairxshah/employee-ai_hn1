"""
Tests for Platinum Tier - Vault Sync
Tests init, pull/push, conflict resolution, gitignore enforcement.
"""

import os
import sys
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(os.path.join(os.path.dirname(__file__), '..')))


class TestVaultSync(unittest.TestCase):
    """Test git-based vault synchronization."""

    def setUp(self):
        """Create a temporary vault for testing."""
        self.test_dir = tempfile.mkdtemp(prefix="test_vault_sync_")
        self.env_patcher = patch.dict(os.environ, {
            'VAULT_PATH': self.test_dir,
            'VAULT_SYNC_ENABLED': 'true',
            'VAULT_REMOTE_URL': '',
            'AGENT_ROLE': 'cloud',
            'AGENT_ID': 'test-sync-agent',
        })
        self.env_patcher.start()

        from vault_sync import VaultSync
        self.sync = VaultSync(vault_path=self.test_dir)

    def tearDown(self):
        self.env_patcher.stop()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_sync_disabled_by_default(self):
        """Sync should be disabled when VAULT_SYNC_ENABLED is false."""
        with patch.dict(os.environ, {'VAULT_SYNC_ENABLED': 'false'}):
            from vault_sync import VaultSync
            sync = VaultSync(vault_path=self.test_dir)
            self.assertFalse(sync.enabled)
            self.assertFalse(sync.init())

    def test_sync_enabled_from_env(self):
        """Sync should be enabled when VAULT_SYNC_ENABLED is true."""
        self.assertTrue(self.sync.enabled)

    def test_init_creates_gitignore(self):
        """init() should create .gitignore with security entries."""
        # First init the git repo
        from vault_sync import VaultSync, GITIGNORE_ENTRIES
        sync = VaultSync(vault_path=self.test_dir)

        # Mock git to avoid actual git operations
        with patch.object(sync, '_run_git') as mock_git:
            mock_git.return_value = (0, "", "")
            with patch.object(sync, 'is_git_repo', return_value=False):
                sync.init()

        gitignore = Path(self.test_dir) / ".gitignore"
        self.assertTrue(gitignore.exists())
        content = gitignore.read_text()
        for entry in GITIGNORE_ENTRIES:
            self.assertIn(entry, content)

    def test_gitignore_blocks_env_files(self):
        """.gitignore should contain .env entry."""
        from vault_sync import GITIGNORE_ENTRIES
        self.assertIn(".env", GITIGNORE_ENTRIES)

    def test_gitignore_blocks_token_files(self):
        """.gitignore should block token files."""
        from vault_sync import GITIGNORE_ENTRIES
        self.assertIn("*.token.json", GITIGNORE_ENTRIES)

    def test_gitignore_blocks_whatsapp_session(self):
        """.gitignore should block WhatsApp session directory."""
        from vault_sync import GITIGNORE_ENTRIES
        self.assertIn(".whatsapp_session/", GITIGNORE_ENTRIES)

    def test_pull_when_disabled(self):
        """pull() should return False when sync is disabled."""
        self.sync.enabled = False
        self.assertFalse(self.sync.pull())

    def test_push_when_disabled(self):
        """push() should return False when sync is disabled."""
        self.sync.enabled = False
        self.assertFalse(self.sync.push())

    def test_sync_calls_pull_and_push(self):
        """sync() should call both pull() and push()."""
        with patch.object(self.sync, 'pull', return_value=True) as mock_pull:
            with patch.object(self.sync, 'push', return_value=True) as mock_push:
                result = self.sync.sync()
                mock_pull.assert_called_once()
                mock_push.assert_called_once()
                self.assertTrue(result)

    def test_is_git_repo_false_for_non_repo(self):
        """is_git_repo() should return False for non-git directory."""
        self.assertFalse(self.sync.is_git_repo())

    def test_gitignore_no_duplicates(self):
        """Enforcing .gitignore twice should not create duplicates."""
        self.sync._enforce_gitignore()
        self.sync._enforce_gitignore()

        gitignore = Path(self.test_dir) / ".gitignore"
        content = gitignore.read_text()
        # Count occurrences of .env
        self.assertEqual(content.count(".env\n"), 1)

    def test_sync_interval_from_env(self):
        """Sync interval should be configurable via env."""
        with patch.dict(os.environ, {'VAULT_SYNC_INTERVAL': '120'}):
            from vault_sync import VaultSync
            sync = VaultSync(vault_path=self.test_dir)
            self.assertEqual(sync.sync_interval, 120)


if __name__ == '__main__':
    unittest.main()
