"""
Claim Manager for Platinum Tier
Atomic claim-by-move protocol using os.rename() for task ownership.
"""

import os
import time
import logging
from pathlib import Path
from typing import Optional, List, Dict

from agent_config import AGENT_ID, get_vault_path
from production_utils import get_structured_logger


logger = get_structured_logger("claim_manager")


class ClaimManager:
    """
    Manages task claiming using atomic file moves (os.rename).

    Workflow:
        Needs_Action/<domain>/file.md
            → claim() → In_Progress/<agent_id>/file.md
            → release_done() → Done/<domain>/file.md
            → release_pending_approval() → Pending_Approval/<domain>/file.md
    """

    def __init__(self, vault_path: Optional[str] = None):
        self.vault_path = Path(vault_path or get_vault_path())
        self.needs_action_dir = self.vault_path / "Needs_Action"
        self.in_progress_dir = self.vault_path / "In_Progress"
        self.done_dir = self.vault_path / "Done"
        self.pending_approval_dir = self.vault_path / "Pending_Approval"

        # Ensure directories exist
        for d in [self.needs_action_dir, self.in_progress_dir, self.done_dir,
                  self.pending_approval_dir]:
            d.mkdir(parents=True, exist_ok=True)

        # Agent-specific working directory
        self.agent_dir = self.in_progress_dir / AGENT_ID
        self.agent_dir.mkdir(parents=True, exist_ok=True)

    def list_available(self, domain: Optional[str] = None) -> List[Path]:
        """
        List files available for claiming in Needs_Action/.

        Args:
            domain: Optional subdomain filter (e.g., 'email', 'social', 'accounting')

        Returns:
            List of file paths available for claiming.
        """
        search_dir = self.needs_action_dir
        if domain:
            search_dir = search_dir / domain
            if not search_dir.exists():
                return []

        files = []
        if search_dir.exists():
            for item in search_dir.rglob("*.md"):
                files.append(item)

        # Sort by modification time (oldest first)
        files.sort(key=lambda p: p.stat().st_mtime)
        return files

    def claim(self, filepath: Path) -> Optional[Path]:
        """
        Claim a task by atomically moving it to In_Progress/<agent_id>/.

        Uses os.rename() which is atomic on the same filesystem.

        Args:
            filepath: Path to the file in Needs_Action/ to claim.

        Returns:
            New path in In_Progress/<agent_id>/ if successful, None if already claimed.
        """
        if not filepath.exists():
            logger.warning(f"File not found (already claimed?): {filepath}")
            return None

        dest = self.agent_dir / filepath.name

        # Handle name collision in agent dir
        if dest.exists():
            stem = filepath.stem
            suffix = filepath.suffix
            dest = self.agent_dir / f"{stem}_{int(time.time())}{suffix}"

        try:
            os.rename(str(filepath), str(dest))
            logger.info(f"Claimed: {filepath.name} -> {dest}")
            return dest
        except OSError as e:
            # Another agent grabbed it first (atomic rename failed)
            logger.info(f"Claim failed (race condition): {filepath.name} - {e}")
            return None

    def release_done(self, filepath: Path, domain: str = "") -> Optional[Path]:
        """
        Release a completed task to Done/.

        Args:
            filepath: Path to the file in In_Progress/<agent_id>/.
            domain: Optional subdomain for the Done/ directory.

        Returns:
            New path in Done/ if successful, None on failure.
        """
        dest_dir = self.done_dir / domain if domain else self.done_dir
        dest_dir.mkdir(parents=True, exist_ok=True)
        return self._move(filepath, dest_dir)

    def release_pending_approval(self, filepath: Path, domain: str = "") -> Optional[Path]:
        """
        Release a task to Pending_Approval/ for human review.

        Args:
            filepath: Path to the file in In_Progress/<agent_id>/.
            domain: Optional subdomain (e.g., 'email', 'social', 'accounting').

        Returns:
            New path in Pending_Approval/ if successful, None on failure.
        """
        dest_dir = self.pending_approval_dir / domain if domain else self.pending_approval_dir
        dest_dir.mkdir(parents=True, exist_ok=True)
        return self._move(filepath, dest_dir)

    def release_back(self, filepath: Path, domain: str = "") -> Optional[Path]:
        """
        Release a task back to Needs_Action/ (unclaim).

        Args:
            filepath: Path to the file in In_Progress/<agent_id>/.
            domain: Optional subdomain.

        Returns:
            New path in Needs_Action/ if successful, None on failure.
        """
        dest_dir = self.needs_action_dir / domain if domain else self.needs_action_dir
        dest_dir.mkdir(parents=True, exist_ok=True)
        return self._move(filepath, dest_dir)

    def is_claimed(self, filename: str) -> bool:
        """Check if a file is currently claimed by any agent."""
        if not self.in_progress_dir.exists():
            return False
        for agent_dir in self.in_progress_dir.iterdir():
            if agent_dir.is_dir():
                if (agent_dir / filename).exists():
                    return True
        return False

    def get_my_claims(self) -> List[Path]:
        """Get all files currently claimed by this agent."""
        if not self.agent_dir.exists():
            return []
        return list(self.agent_dir.glob("*.md"))

    def _move(self, filepath: Path, dest_dir: Path) -> Optional[Path]:
        """Move a file to a destination directory."""
        if not filepath.exists():
            logger.warning(f"File not found: {filepath}")
            return None

        dest = dest_dir / filepath.name

        # Handle name collision
        if dest.exists():
            stem = filepath.stem
            suffix = filepath.suffix
            dest = dest_dir / f"{stem}_{int(time.time())}{suffix}"

        try:
            os.rename(str(filepath), str(dest))
            logger.info(f"Moved: {filepath.name} -> {dest}")
            return dest
        except OSError as e:
            logger.error(f"Move failed: {filepath.name} - {e}")
            return None
