"""
Vault Sync for Platinum Tier
Git-based vault synchronization: pull (rebase), push, conflict resolution, .gitignore enforcement.
"""

import os
import subprocess
import time
import logging
from pathlib import Path
from typing import Optional, Tuple

from production_utils import get_structured_logger


logger = get_structured_logger("vault_sync")

# Secrets that must NEVER be synced
GITIGNORE_ENTRIES = [
    ".env",
    "*.token.json",
    ".facebook_token.json",
    ".twitter_token.json",
    ".linkedin_token.json",
    ".gmail_token.json",
    ".whatsapp_session/",
    "__pycache__/",
    "*.pyc",
    ".obsidian/workspace.json",
    ".obsidian/workspace-mobile.json",
]


class VaultSync:
    """
    Git-based vault synchronization between Cloud and Local agents.

    Usage:
        sync = VaultSync("/path/to/vault", remote_url="git@github.com:user/vault.git")
        sync.init()       # One-time setup
        sync.pull()       # Pull latest changes (rebase)
        sync.push()       # Push local changes
        sync.sync()       # Pull + push in one call
    """

    def __init__(self, vault_path: Optional[str] = None,
                 remote_url: Optional[str] = None,
                 branch: str = "main"):
        self.vault_path = Path(vault_path or os.getenv(
            "VAULT_PATH", r"D:\prompteng\AI_Employee_Vault"
        ))
        self.remote_url = remote_url or os.getenv("VAULT_REMOTE_URL", "")
        self.branch = branch
        self.enabled = os.getenv("VAULT_SYNC_ENABLED", "false").lower() == "true"
        self.sync_interval = int(os.getenv("VAULT_SYNC_INTERVAL", "60"))

    def _run_git(self, *args, check: bool = True) -> Tuple[int, str, str]:
        """Run a git command in the vault directory."""
        cmd = ["git", "-C", str(self.vault_path)] + list(args)
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if check and result.returncode != 0:
                logger.error(f"git {' '.join(args)} failed: {result.stderr.strip()}")
            return result.returncode, result.stdout.strip(), result.stderr.strip()
        except subprocess.TimeoutExpired:
            logger.error(f"git {' '.join(args)} timed out")
            return 1, "", "timeout"
        except FileNotFoundError:
            logger.error("git not found on PATH")
            return 1, "", "git not found"

    def is_git_repo(self) -> bool:
        """Check if the vault is already a git repo."""
        code, _, _ = self._run_git("rev-parse", "--is-inside-work-tree", check=False)
        return code == 0

    def init(self) -> bool:
        """
        Initialize the vault as a git repo (if not already) and configure remote.
        Also enforces .gitignore for secrets.
        """
        if not self.enabled:
            logger.info("Vault sync is disabled (VAULT_SYNC_ENABLED != true)")
            return False

        if not self.vault_path.exists():
            logger.error(f"Vault path does not exist: {self.vault_path}")
            return False

        # Init repo if needed
        if not self.is_git_repo():
            code, _, err = self._run_git("init")
            if code != 0:
                logger.error(f"Failed to init git repo: {err}")
                return False
            logger.info(f"Initialized git repo at {self.vault_path}")

        # Enforce .gitignore
        self._enforce_gitignore()

        # Add remote if provided
        if self.remote_url:
            # Check if origin already exists
            code, out, _ = self._run_git("remote", "get-url", "origin", check=False)
            if code != 0:
                self._run_git("remote", "add", "origin", self.remote_url)
                logger.info(f"Added remote origin: {self.remote_url}")
            elif out != self.remote_url:
                self._run_git("remote", "set-url", "origin", self.remote_url)
                logger.info(f"Updated remote origin: {self.remote_url}")

        return True

    def _enforce_gitignore(self):
        """Ensure .gitignore contains all required secret exclusions."""
        gitignore_path = self.vault_path / ".gitignore"

        existing = set()
        if gitignore_path.exists():
            existing = set(gitignore_path.read_text(encoding="utf-8").splitlines())

        missing = [entry for entry in GITIGNORE_ENTRIES if entry not in existing]

        if missing:
            with open(gitignore_path, "a", encoding="utf-8") as f:
                if existing and not gitignore_path.read_text().endswith("\n"):
                    f.write("\n")
                f.write("# Platinum tier - secrets exclusion\n")
                for entry in missing:
                    f.write(f"{entry}\n")
            logger.info(f"Added {len(missing)} entries to .gitignore")

    def pull(self) -> bool:
        """Pull latest changes from remote using rebase to keep history linear."""
        if not self.enabled:
            return False

        # Stage any local changes first (to avoid rebase conflicts with unstaged)
        self._run_git("add", "-A", check=False)

        # Stash local changes if any
        code, out, _ = self._run_git("stash", check=False)
        stashed = "No local changes" not in out and code == 0

        # Pull with rebase
        code, out, err = self._run_git("pull", "--rebase", "origin", self.branch, check=False)

        if code != 0:
            if "CONFLICT" in err or "CONFLICT" in out:
                logger.warning("Merge conflict detected, resolving with ours strategy")
                self._resolve_conflicts()
            elif "fatal" in err:
                logger.error(f"Pull failed: {err}")
                if stashed:
                    self._run_git("stash", "pop", check=False)
                return False

        # Restore stashed changes
        if stashed:
            code, _, err = self._run_git("stash", "pop", check=False)
            if code != 0 and "CONFLICT" in err:
                logger.warning("Stash pop conflict, keeping local changes")
                self._run_git("checkout", "--theirs", ".", check=False)
                self._run_git("add", "-A", check=False)

        logger.info("Pull completed")
        return True

    def push(self) -> bool:
        """Commit and push local changes to remote."""
        if not self.enabled:
            return False

        # Stage all changes
        self._run_git("add", "-A")

        # Check if there are changes to commit
        code, out, _ = self._run_git("status", "--porcelain", check=False)
        if not out.strip():
            logger.debug("No changes to push")
            return True

        # Commit
        from agent_config import AGENT_ID
        commit_msg = f"[{AGENT_ID}] auto-sync {time.strftime('%Y-%m-%d %H:%M:%S')}"
        code, _, err = self._run_git("commit", "-m", commit_msg, check=False)
        if code != 0:
            logger.error(f"Commit failed: {err}")
            return False

        # Push
        code, _, err = self._run_git("push", "origin", self.branch, check=False)
        if code != 0:
            logger.error(f"Push failed: {err}")
            # Try pull-rebase-push
            if self.pull():
                code, _, err = self._run_git("push", "origin", self.branch, check=False)
                if code != 0:
                    logger.error(f"Push after rebase failed: {err}")
                    return False
            else:
                return False

        logger.info("Push completed")
        return True

    def sync(self) -> bool:
        """Full sync cycle: pull then push."""
        if not self.enabled:
            return False

        pull_ok = self.pull()
        push_ok = self.push()
        return pull_ok and push_ok

    def _resolve_conflicts(self):
        """Resolve merge conflicts by keeping local changes (ours)."""
        self._run_git("checkout", "--ours", ".", check=False)
        self._run_git("add", "-A", check=False)
        self._run_git("rebase", "--continue", check=False)
        logger.info("Conflict resolved with local (ours) strategy")

    def run_sync_loop(self):
        """Run continuous sync loop (for use in orchestrators)."""
        logger.info(f"Starting vault sync loop (interval: {self.sync_interval}s)")
        while True:
            try:
                self.sync()
            except Exception as e:
                logger.error(f"Sync loop error: {e}")
            time.sleep(self.sync_interval)
