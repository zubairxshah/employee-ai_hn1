"""
Cloud Orchestrator for Platinum Tier
Main loop: sync → run watchers → claim tasks → draft responses → sync.

Runs on the cloud VM (or locally with AGENT_ROLE=cloud for testing).
Only performs read/draft operations — never sends, posts, or confirms.
"""

import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent))

from agent_config import is_cloud, AGENT_ID, AGENT_ROLE, CLOUD, get_vault_path
from vault_sync import VaultSync
from claim_manager import ClaimManager
from dashboard_manager import DashboardManager
from production_utils import get_structured_logger
from security_config import security_config


logger = get_structured_logger("cloud_orchestrator")


class CloudOrchestrator:
    """
    Cloud agent main loop.

    Responsibilities:
    - Sync vault with remote (pull latest, push results)
    - Scan Needs_Action/ for unclaimed tasks
    - Claim tasks atomically
    - Process tasks: email triage → draft, social → draft, accounting → read/draft
    - Write updates to Updates/ for Local to merge into Dashboard
    - Write signals to Signals/ for Local to act on
    """

    def __init__(self, poll_interval: int = 30):
        self.poll_interval = poll_interval
        self.vault_path = Path(get_vault_path())
        self.vault_sync = VaultSync()
        self.claim_mgr = ClaimManager()
        self.dashboard = DashboardManager()
        self.running = True

    def start(self):
        """Start the cloud orchestrator."""
        logger.info(f"Cloud Orchestrator starting (agent_id={AGENT_ID})")
        logger.info(f"Vault: {self.vault_path}")
        logger.info(f"Poll interval: {self.poll_interval}s")

        # Safety check
        if not security_config.validate_cloud_safety():
            logger.critical("Cloud safety validation FAILED. Refusing to start.")
            sys.exit(1)

        # Initialize vault sync
        self.vault_sync.init()

        print("=" * 60)
        print(f"Cloud Orchestrator [{AGENT_ID}]")
        print(f"Vault: {self.vault_path}")
        print(f"Sync enabled: {self.vault_sync.enabled}")
        print("=" * 60)

        try:
            while self.running:
                self._run_cycle()
                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            logger.info("Cloud Orchestrator shutting down...")
        finally:
            # Final sync
            self.vault_sync.push()
            logger.info("Cloud Orchestrator stopped")

    def _run_cycle(self):
        """Run one orchestration cycle."""
        cycle_start = time.time()

        try:
            # Step 1: Sync (pull latest)
            self.vault_sync.pull()

            # Step 2: Process each domain
            self._process_email_tasks()
            self._process_social_tasks()
            self._process_accounting_tasks()

            # Step 3: Sync (push results)
            self.vault_sync.push()

            elapsed = time.time() - cycle_start
            logger.debug(f"Cycle completed in {elapsed:.1f}s")

        except Exception as e:
            logger.error(f"Cycle error: {e}")

    def _process_email_tasks(self):
        """Process email tasks: triage → create drafts."""
        available = self.claim_mgr.list_available(domain="email")
        for filepath in available:
            claimed = self.claim_mgr.claim(filepath)
            if not claimed:
                continue

            try:
                task_data = self._read_task(claimed)
                logger.info(f"Processing email task: {claimed.name}")

                # Create a draft file in Pending_Approval/email/
                draft_content = self._create_email_draft(task_data)
                draft_filename = f"EMAIL_DRAFT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
                draft_path = self.vault_path / "Pending_Approval" / "email" / draft_filename
                draft_path.parent.mkdir(parents=True, exist_ok=True)
                draft_path.write_text(draft_content, encoding="utf-8")

                # Move original to done
                self.claim_mgr.release_done(claimed, domain="email")

                # Write update
                self.dashboard.write_update("email_draft", {
                    "summary": f"Email draft created: {draft_filename}",
                    "draft_path": str(draft_path),
                })

                # Signal local
                self.dashboard.write_signal("new_draft_ready", {
                    "domain": "email",
                    "draft_path": str(draft_path),
                    "filename": draft_filename,
                })

                logger.info(f"Email draft created: {draft_filename}")

            except Exception as e:
                logger.error(f"Error processing email task {claimed.name}: {e}")
                self.claim_mgr.release_back(claimed, domain="email")

    def _process_social_tasks(self):
        """Process social tasks: create drafts for Facebook/Twitter/LinkedIn."""
        available = self.claim_mgr.list_available(domain="social")
        for filepath in available:
            claimed = self.claim_mgr.claim(filepath)
            if not claimed:
                continue

            try:
                task_data = self._read_task(claimed)
                logger.info(f"Processing social task: {claimed.name}")

                # Determine platform from task data
                platform = task_data.get("platform", "facebook")
                draft_content = self._create_social_draft(task_data, platform)
                draft_filename = f"SOCIAL_DRAFT_{platform}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
                draft_path = self.vault_path / "Pending_Approval" / "social" / draft_filename
                draft_path.parent.mkdir(parents=True, exist_ok=True)
                draft_path.write_text(draft_content, encoding="utf-8")

                self.claim_mgr.release_done(claimed, domain="social")

                self.dashboard.write_update("social_draft", {
                    "summary": f"Social draft created for {platform}: {draft_filename}",
                    "platform": platform,
                })

                self.dashboard.write_signal("new_draft_ready", {
                    "domain": "social",
                    "platform": platform,
                    "draft_path": str(draft_path),
                    "filename": draft_filename,
                })

                logger.info(f"Social draft created: {draft_filename}")

            except Exception as e:
                logger.error(f"Error processing social task {claimed.name}: {e}")
                self.claim_mgr.release_back(claimed, domain="social")

    def _process_accounting_tasks(self):
        """Process accounting tasks: read data, create draft invoices."""
        available = self.claim_mgr.list_available(domain="accounting")
        for filepath in available:
            claimed = self.claim_mgr.claim(filepath)
            if not claimed:
                continue

            try:
                task_data = self._read_task(claimed)
                logger.info(f"Processing accounting task: {claimed.name}")

                # Create draft for approval (cloud cannot confirm/pay)
                draft_content = self._create_accounting_draft(task_data)
                draft_filename = f"ACCT_DRAFT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
                draft_path = self.vault_path / "Pending_Approval" / "accounting" / draft_filename
                draft_path.parent.mkdir(parents=True, exist_ok=True)
                draft_path.write_text(draft_content, encoding="utf-8")

                self.claim_mgr.release_done(claimed, domain="accounting")

                self.dashboard.write_update("accounting_draft", {
                    "summary": f"Accounting draft created: {draft_filename}",
                })

                logger.info(f"Accounting draft created: {draft_filename}")

            except Exception as e:
                logger.error(f"Error processing accounting task {claimed.name}: {e}")
                self.claim_mgr.release_back(claimed, domain="accounting")

    def _read_task(self, filepath: Path) -> Dict[str, Any]:
        """Read and parse a task file (markdown with optional frontmatter)."""
        content = filepath.read_text(encoding="utf-8")
        data = {"raw_content": content, "filename": filepath.name}

        # Parse frontmatter if present
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                for line in parts[1].strip().split("\n"):
                    if ":" in line:
                        key, val = line.split(":", 1)
                        data[key.strip()] = val.strip()
                data["body"] = parts[2].strip()

        return data

    def _create_email_draft(self, task_data: Dict) -> str:
        """Create an email draft markdown file."""
        now = datetime.now().isoformat()
        to = task_data.get("to", task_data.get("recipient", ""))
        subject = task_data.get("subject", "")
        body = task_data.get("body", task_data.get("raw_content", ""))

        return f"""---
type: send_email
action: send_email
to: {to}
subject: {subject}
created_by: {AGENT_ID}
created_at: {now}
status: pending_approval
---

## Email Draft

**To:** {to}
**Subject:** {subject}

### Body
{body}

---
*Draft created by Cloud Agent. Approve to send.*
"""

    def _create_social_draft(self, task_data: Dict, platform: str) -> str:
        """Create a social media draft markdown file."""
        now = datetime.now().isoformat()
        text = task_data.get("text", task_data.get("body", task_data.get("raw_content", "")))

        return f"""---
type: social_post
action: create_post
platform: {platform}
created_by: {AGENT_ID}
created_at: {now}
status: pending_approval
---

## Social Media Draft ({platform.title()})

### Content
{text}

---
*Draft created by Cloud Agent. Approve to post.*
"""

    def _create_accounting_draft(self, task_data: Dict) -> str:
        """Create an accounting draft markdown file."""
        now = datetime.now().isoformat()
        action = task_data.get("action", "confirm_invoice")
        invoice_id = task_data.get("invoice_id", "")
        amount = task_data.get("amount", "")

        return f"""---
type: accounting
action: {action}
invoice_id: {invoice_id}
amount: {amount}
created_by: {AGENT_ID}
created_at: {now}
status: pending_approval
---

## Accounting Draft

**Action:** {action}
**Invoice ID:** {invoice_id}
**Amount:** {amount}

### Details
{task_data.get('body', task_data.get('raw_content', 'No details provided.'))}

---
*Draft created by Cloud Agent. Approve to execute.*
"""


def main():
    """Entry point for the cloud orchestrator."""
    # Force cloud role
    os.environ.setdefault("AGENT_ROLE", CLOUD)

    poll_interval = int(os.getenv("CLOUD_POLL_INTERVAL", "30"))
    orchestrator = CloudOrchestrator(poll_interval=poll_interval)
    orchestrator.start()


if __name__ == "__main__":
    main()
