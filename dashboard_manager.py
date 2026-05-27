"""
Dashboard Manager for Platinum Tier
Single-writer rule: Cloud writes to Updates/, Local merges into Dashboard.md
"""

import os
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

from agent_config import is_cloud, is_local, get_vault_path, AGENT_ID
from production_utils import get_structured_logger


logger = get_structured_logger("dashboard_manager")


class DashboardManager:
    """
    Manages the Dashboard.md file and Updates/ directory.

    Cloud writes status updates to Updates/<timestamp>_<type>.json.
    Local reads Updates/ and merges them into Dashboard.md (single-writer rule).
    """

    def __init__(self, vault_path: Optional[str] = None):
        self.vault_path = Path(vault_path or get_vault_path())
        self.updates_dir = self.vault_path / "Updates"
        self.dashboard_path = self.vault_path / "Dashboard.md"
        self.updates_dir.mkdir(parents=True, exist_ok=True)

    # ==================== CLOUD: Write Updates ====================

    def write_update(self, update_type: str, data: Dict[str, Any]) -> Path:
        """
        Write a status update file to Updates/ (used by Cloud agent).

        Args:
            update_type: Type of update (e.g., 'email_draft', 'task_complete', 'health')
            data: Update data dictionary.

        Returns:
            Path to the created update file.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{update_type}.json"
        filepath = self.updates_dir / filename

        update = {
            "timestamp": datetime.now().isoformat(),
            "type": update_type,
            "agent_id": AGENT_ID,
            "data": data,
        }

        filepath.write_text(json.dumps(update, indent=2), encoding="utf-8")
        logger.info(f"Update written: {filename}")
        return filepath

    # ==================== LOCAL: Merge Updates into Dashboard ====================

    def merge_updates_into_dashboard(self) -> int:
        """
        Read all updates from Updates/ and merge them into Dashboard.md.
        Only the Local agent should call this (single-writer rule).

        Returns:
            Number of updates merged.
        """
        if not is_local():
            logger.warning("Only the Local agent should merge updates into Dashboard")
            return 0

        updates = self._read_pending_updates()
        if not updates:
            return 0

        # Build dashboard content
        dashboard_content = self._build_dashboard(updates)

        # Write dashboard
        self.dashboard_path.write_text(dashboard_content, encoding="utf-8")
        logger.info(f"Dashboard updated with {len(updates)} new updates")

        # Archive processed update files
        self._archive_updates(updates)

        return len(updates)

    def _read_pending_updates(self) -> List[Dict]:
        """Read all pending update files from Updates/."""
        updates = []
        if not self.updates_dir.exists():
            return updates

        for filepath in sorted(self.updates_dir.glob("*.json")):
            try:
                data = json.loads(filepath.read_text(encoding="utf-8"))
                data["_filepath"] = str(filepath)
                updates.append(data)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Failed to read update {filepath.name}: {e}")

        return updates

    def _build_dashboard(self, new_updates: List[Dict]) -> str:
        """Build the Dashboard.md content."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Read existing dashboard if it exists
        existing_log = ""
        if self.dashboard_path.exists():
            content = self.dashboard_path.read_text(encoding="utf-8")
            # Extract existing activity log
            log_marker = "## Activity Log\n"
            idx = content.find(log_marker)
            if idx >= 0:
                existing_log = content[idx + len(log_marker):]

        # Build new entries
        new_entries = []
        for update in new_updates:
            ts = update.get("timestamp", "")
            utype = update.get("type", "unknown")
            agent = update.get("agent_id", "unknown")
            data = update.get("data", {})
            summary = data.get("summary", json.dumps(data)[:200])
            new_entries.append(f"- **[{ts}]** `{utype}` from `{agent}`: {summary}")

        new_entries_text = "\n".join(new_entries)

        dashboard = f"""# AI Employee Dashboard
> Last updated: {now}

## Recent Updates
{new_entries_text}

## Activity Log
{new_entries_text}
{existing_log}"""

        return dashboard

    def _archive_updates(self, updates: List[Dict]):
        """Delete processed update files."""
        for update in updates:
            filepath = update.get("_filepath")
            if filepath:
                try:
                    os.remove(filepath)
                except OSError:
                    pass

    # ==================== SIGNALS ====================

    def write_signal(self, signal_type: str, data: Dict[str, Any]) -> Path:
        """
        Write a signal file for the other agent to pick up.
        Cloud writes signals for Local (e.g., 'new_draft_ready', 'task_complete').

        Args:
            signal_type: Signal type identifier.
            data: Signal payload.

        Returns:
            Path to the created signal file.
        """
        signals_dir = self.vault_path / "Signals"
        signals_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{signal_type}.json"
        filepath = signals_dir / filename

        signal = {
            "timestamp": datetime.now().isoformat(),
            "signal": signal_type,
            "agent_id": AGENT_ID,
            "data": data,
        }

        filepath.write_text(json.dumps(signal, indent=2), encoding="utf-8")
        logger.info(f"Signal written: {filename}")
        return filepath

    def read_signals(self) -> List[Dict]:
        """Read and consume all pending signals."""
        signals_dir = self.vault_path / "Signals"
        if not signals_dir.exists():
            return []

        signals = []
        for filepath in sorted(signals_dir.glob("*.json")):
            try:
                data = json.loads(filepath.read_text(encoding="utf-8"))
                signals.append(data)
                os.remove(filepath)  # Consume signal
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Failed to read signal {filepath.name}: {e}")

        return signals
