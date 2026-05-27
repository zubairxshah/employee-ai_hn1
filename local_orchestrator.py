"""
Local Orchestrator for Platinum Tier
Main loop: sync → merge Updates → process Approved → notify pending → sync.

Runs on the local Windows machine when the user is active.
Handles approvals, WhatsApp notifications, payments, and final send/post actions.
"""

import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import requests

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent))

from agent_config import is_local, AGENT_ID, AGENT_ROLE, LOCAL, get_vault_path, can_execute_action
from vault_sync import VaultSync
from claim_manager import ClaimManager
from dashboard_manager import DashboardManager
from production_utils import get_structured_logger, MCPClient


logger = get_structured_logger("local_orchestrator")


class LocalOrchestrator:
    """
    Local agent main loop.

    Responsibilities:
    - Sync vault with remote (pull cloud results, push local changes)
    - Merge Updates/ into Dashboard.md
    - Process Signals/ from cloud
    - Execute approved actions (email send, social post, invoice confirm, payment)
    - Send WhatsApp notifications for new pending approvals
    """

    def __init__(self, poll_interval: int = 10):
        self.poll_interval = poll_interval
        self.vault_path = Path(get_vault_path())
        self.vault_sync = VaultSync()
        self.claim_mgr = ClaimManager()
        self.dashboard = DashboardManager()
        self.running = True

        # MCP clients for executing approved actions
        self.email_mcp = MCPClient("http://localhost:8001", "email")
        self.facebook_mcp = MCPClient("http://localhost:8006", "facebook")
        self.twitter_mcp = MCPClient("http://localhost:8007", "twitter")
        self.linkedin_mcp = MCPClient("http://localhost:8002", "linkedin")
        self.odoo_mcp = MCPClient("http://localhost:8005", "odoo")
        self.whatsapp_mcp = MCPClient("http://localhost:8004", "whatsapp", timeout=60)

    def start(self):
        """Start the local orchestrator."""
        logger.info(f"Local Orchestrator starting (agent_id={AGENT_ID})")
        logger.info(f"Vault: {self.vault_path}")
        logger.info(f"Poll interval: {self.poll_interval}s")

        # Initialize vault sync
        self.vault_sync.init()

        print("=" * 60)
        print(f"Local Orchestrator [{AGENT_ID}]")
        print(f"Vault: {self.vault_path}")
        print(f"Sync enabled: {self.vault_sync.enabled}")
        print("=" * 60)

        try:
            while self.running:
                self._run_cycle()
                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            logger.info("Local Orchestrator shutting down...")
        finally:
            self.vault_sync.push()
            logger.info("Local Orchestrator stopped")

    def _run_cycle(self):
        """Run one orchestration cycle."""
        cycle_start = time.time()

        try:
            # Step 1: Sync (pull cloud changes)
            self.vault_sync.pull()

            # Step 2: Merge updates into dashboard
            merged = self.dashboard.merge_updates_into_dashboard()
            if merged > 0:
                logger.info(f"Merged {merged} updates into Dashboard")

            # Step 3: Process signals from cloud
            self._process_signals()

            # Step 4: Execute approved actions
            self._execute_approved_actions()

            # Step 5: Notify about new pending approvals
            self._notify_pending_approvals()

            # Step 6: Sync (push local changes)
            self.vault_sync.push()

            elapsed = time.time() - cycle_start
            logger.debug(f"Cycle completed in {elapsed:.1f}s")

        except Exception as e:
            logger.error(f"Cycle error: {e}")

    def _process_signals(self):
        """Process signals from the Cloud agent."""
        signals = self.dashboard.read_signals()
        for signal in signals:
            signal_type = signal.get("signal", "")
            data = signal.get("data", {})

            if signal_type == "new_draft_ready":
                domain = data.get("domain", "")
                filename = data.get("filename", "")
                logger.info(f"Signal: new draft ready in {domain}: {filename}")
                # The draft is already in Pending_Approval/, user will review in Obsidian

            elif signal_type == "health_alert":
                logger.warning(f"Signal: health alert from cloud: {data}")
                self._send_whatsapp_alert(
                    f"Cloud Health Alert\n{data.get('message', 'Unknown issue')}"
                )

            else:
                logger.info(f"Signal: {signal_type}: {data}")

    def _execute_approved_actions(self):
        """Scan Approved/ directories and execute approved actions."""
        approved_base = self.vault_path / "Approved"
        if not approved_base.exists():
            return

        # Scan all subdirectories
        for approved_file in approved_base.rglob("*.md"):
            try:
                self._execute_single_approved(approved_file)
            except Exception as e:
                logger.error(f"Error executing {approved_file.name}: {e}")

    def _execute_single_approved(self, filepath: Path):
        """Execute a single approved action."""
        content = filepath.read_text(encoding="utf-8")
        task_data = self._parse_frontmatter(content)
        action = task_data.get("action", task_data.get("type", ""))

        if not can_execute_action(action):
            logger.warning(f"Action '{action}' not allowed for {AGENT_ROLE} agent")
            return

        logger.info(f"Executing approved action: {action} ({filepath.name})")

        success = False

        if action == "send_email":
            success = self._execute_email(task_data)
        elif action == "create_post":
            success = self._execute_social_post(task_data)
        elif action == "confirm_invoice":
            success = self._execute_confirm_invoice(task_data)
        elif action == "register_payment":
            success = self._execute_register_payment(task_data)
        else:
            logger.info(f"Unknown action type: {action}, marking as done")
            success = True

        if success:
            # Move to Done/
            done_dir = self.vault_path / "Done"
            domain = filepath.parent.name if filepath.parent.name != "Approved" else ""
            if domain:
                done_dir = done_dir / domain
            done_dir.mkdir(parents=True, exist_ok=True)

            dest = done_dir / filepath.name
            if dest.exists():
                stem = filepath.stem
                dest = done_dir / f"{stem}_{int(time.time())}.md"

            os.rename(str(filepath), str(dest))
            logger.info(f"Moved to Done: {filepath.name}")

    def _execute_email(self, data: Dict) -> bool:
        """Execute an approved email send."""
        result = self.email_mcp.post("send_email", {
            "to": data.get("to", ""),
            "subject": data.get("subject", ""),
            "body": data.get("body", ""),
        })
        if result.get("success"):
            logger.info(f"Email sent to {data.get('to')}")
            return True
        logger.error(f"Email send failed: {result.get('error')}")
        return False

    def _execute_social_post(self, data: Dict) -> bool:
        """Execute an approved social media post."""
        platform = data.get("platform", "facebook")
        text = data.get("text", data.get("body", ""))

        if platform == "facebook":
            result = self.facebook_mcp.post("create_post", {"message": text})
        elif platform == "twitter":
            result = self.twitter_mcp.post("create_tweet", {"text": text})
        elif platform == "linkedin":
            result = self.linkedin_mcp.post("create_post", {"text": text})
        elif platform == "instagram":
            result = self.facebook_mcp.post("create_instagram_post", {
                "caption": text,
                "image_url": data.get("image_url", ""),
            })
        else:
            logger.warning(f"Unknown social platform: {platform}")
            return False

        if result.get("success"):
            logger.info(f"Social post published on {platform}")
            return True
        logger.error(f"Social post failed on {platform}: {result.get('error')}")
        return False

    def _execute_confirm_invoice(self, data: Dict) -> bool:
        """Execute an approved invoice confirmation."""
        invoice_id = data.get("invoice_id")
        if not invoice_id:
            logger.error("No invoice_id in approved data")
            return False

        result = self.odoo_mcp.post("confirm_invoice", {
            "invoice_id": int(invoice_id),
        })
        if result.get("success"):
            logger.info(f"Invoice {invoice_id} confirmed")
            return True
        logger.error(f"Invoice confirm failed: {result.get('error')}")
        return False

    def _execute_register_payment(self, data: Dict) -> bool:
        """Execute an approved payment registration."""
        result = self.odoo_mcp.post("register_payment", {
            "invoice_id": int(data.get("invoice_id", 0)),
            "amount": float(data.get("amount", 0)),
        })
        if result.get("success"):
            logger.info(f"Payment registered for invoice {data.get('invoice_id')}")
            return True
        logger.error(f"Payment registration failed: {result.get('error')}")
        return False

    def _notify_pending_approvals(self):
        """Send WhatsApp notifications for new pending approvals."""
        pending_dirs = [
            self.vault_path / "Pending_Approval" / "email",
            self.vault_path / "Pending_Approval" / "social",
            self.vault_path / "Pending_Approval" / "accounting",
            self.vault_path / "Pending_Approval",
        ]

        for pending_dir in pending_dirs:
            if not pending_dir.exists():
                continue
            for item in pending_dir.glob("*.md"):
                content = item.read_text(encoding="utf-8")
                if "whatsapp_notified: true" in content:
                    continue

                # Send notification
                self._send_whatsapp_alert(
                    f"New approval needed:\n{item.name}\nReview in Obsidian vault."
                )

                # Mark as notified
                if content.startswith("---"):
                    end = content.find("---", 3)
                    if end > 0:
                        content = content[:end] + "whatsapp_notified: true\n" + content[end:]
                        item.write_text(content, encoding="utf-8")

    def _send_whatsapp_alert(self, message: str):
        """Send a WhatsApp notification."""
        try:
            result = self.whatsapp_mcp.post("send_notification", {
                "message": message,
            })
            if result.get("success"):
                logger.info("WhatsApp alert sent")
        except Exception as e:
            logger.debug(f"WhatsApp alert failed (non-critical): {e}")

    def _parse_frontmatter(self, content: str) -> Dict[str, str]:
        """Parse YAML-like frontmatter from markdown content."""
        data = {}
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                for line in parts[1].strip().split("\n"):
                    if ":" in line:
                        key, val = line.split(":", 1)
                        data[key.strip()] = val.strip()
                data["body"] = parts[2].strip()
        return data


def main():
    """Entry point for the local orchestrator."""
    os.environ.setdefault("AGENT_ROLE", LOCAL)

    poll_interval = int(os.getenv("LOCAL_POLL_INTERVAL", "10"))
    orchestrator = LocalOrchestrator(poll_interval=poll_interval)
    orchestrator.start()


if __name__ == "__main__":
    main()
