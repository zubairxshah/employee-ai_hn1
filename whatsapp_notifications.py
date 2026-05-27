"""
WhatsApp Notification Service
Sends payment reminders, approval alerts, and daily summaries via WhatsApp MCP

Standalone runner with configurable poll interval.
"""

import os
import sys
import json
import time
import logging
import requests
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from production_utils import get_structured_logger, MCPClient


VAULT_PATH = os.getenv('VAULT_PATH', r'D:\prompteng\AI_Employee_Vault')
STATE_FILE = os.path.join(VAULT_PATH, 'Logs', 'notification_state.json')

# MCP clients
WHATSAPP_MCP = MCPClient('http://localhost:8004', 'whatsapp', timeout=60)
ODOO_MCP = MCPClient('http://localhost:8005', 'odoo', timeout=30)


class WhatsAppNotificationService:
    """
    Service that monitors Odoo and the Vault for items requiring attention,
    then sends WhatsApp notifications.

    Features:
    - Payment reminder notifications for overdue invoices (via Odoo MCP)
    - Approval alert notifications for new pending items (via Vault scan)
    - Daily summary combining reminders + alerts
    - Cooldown/dedup via state persistence
    """

    def __init__(self, poll_interval: int = 300, cooldown_hours: int = 24,
                 phone: str = None):
        """
        Args:
            poll_interval: Seconds between notification cycles (default: 5 min)
            cooldown_hours: Hours before re-notifying about the same item
            phone: Override phone number (else uses WhatsApp MCP default)
        """
        self.poll_interval = poll_interval
        self.cooldown_hours = cooldown_hours
        self.phone = phone
        self.logger = get_structured_logger('whatsapp_notifications')
        self.state = self._load_state()

    # ==================== STATE PERSISTENCE ====================

    def _load_state(self) -> dict:
        """Load notification state from JSON file"""
        try:
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE, 'r') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.warning(f"Failed to load notification state: {e}")

        return {
            "last_payment_check": None,
            "last_approval_check": None,
            "last_daily_summary": None,
            "notified_invoices": {},   # invoice_id -> last_notified_iso
            "notified_approvals": {},  # filename -> last_notified_iso
        }

    def _save_state(self):
        """Save notification state to JSON file"""
        try:
            Path(os.path.dirname(STATE_FILE)).mkdir(parents=True, exist_ok=True)
            with open(STATE_FILE, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            self.logger.warning(f"Failed to save notification state: {e}")

    def _is_in_cooldown(self, item_id: str, category: str) -> bool:
        """Check if an item is still in cooldown period"""
        key = f"notified_{category}"
        notified = self.state.get(key, {})
        last_notified = notified.get(item_id)

        if not last_notified:
            return False

        try:
            last_dt = datetime.fromisoformat(last_notified)
            return datetime.now() < last_dt + timedelta(hours=self.cooldown_hours)
        except Exception:
            return False

    def _mark_notified(self, item_id: str, category: str):
        """Mark an item as notified (starts cooldown)"""
        key = f"notified_{category}"
        if key not in self.state:
            self.state[key] = {}
        self.state[key][item_id] = datetime.now().isoformat()
        self._save_state()

    # ==================== NOTIFICATION METHODS ====================

    def _send_whatsapp(self, message: str) -> bool:
        """Send a WhatsApp message via the WhatsApp MCP server"""
        try:
            payload = {"message": message}
            if self.phone:
                payload["phone"] = self.phone

            # Use send_notification for structured alerts, send_custom_message for free-form
            result = WHATSAPP_MCP.post('send_custom_message', payload)

            if result.get('success'):
                self.logger.info("WhatsApp notification sent successfully")
                return True
            else:
                self.logger.error(f"WhatsApp send failed: {result.get('error')}")
                return False

        except Exception as e:
            self.logger.error(f"WhatsApp notification error: {e}")
            return False

    def check_and_send_payment_reminders(self) -> int:
        """
        Query Odoo for overdue invoices and send WhatsApp reminders.
        Returns number of reminders sent.
        """
        sent_count = 0

        try:
            # Query Odoo for overdue invoices
            result = ODOO_MCP.post('get_invoices', {
                "state": "posted",
                "payment_state": "not_paid"
            })

            if not result.get('success'):
                self.logger.warning(f"Odoo invoice query failed: {result.get('error')}")
                return 0

            invoices = result.get('invoices', [])
            overdue = []

            for inv in invoices:
                due_date = inv.get('invoice_date_due', '')
                if due_date:
                    try:
                        due = datetime.fromisoformat(due_date)
                        if due < datetime.now():
                            overdue.append(inv)
                    except Exception:
                        pass

            for inv in overdue:
                inv_id = str(inv.get('id', ''))
                if self._is_in_cooldown(inv_id, 'invoices'):
                    continue

                partner = inv.get('partner_name', inv.get('partner_id', 'Unknown'))
                amount = inv.get('amount_total', 0)
                due_date = inv.get('invoice_date_due', 'N/A')
                inv_number = inv.get('name', inv_id)

                message = (
                    f"Payment Reminder\n\n"
                    f"Invoice: {inv_number}\n"
                    f"Customer: {partner}\n"
                    f"Amount: ${amount:.2f}\n"
                    f"Due Date: {due_date}\n"
                    f"Status: OVERDUE\n\n"
                    f"Please follow up on this payment."
                )

                if self._send_whatsapp(message):
                    self._mark_notified(inv_id, 'invoices')
                    sent_count += 1

            self.state['last_payment_check'] = datetime.now().isoformat()
            self._save_state()

        except Exception as e:
            self.logger.error(f"Payment reminder check failed: {e}")

        return sent_count

    def check_and_send_approval_alerts(self) -> int:
        """
        Scan Pending_Approval/ for new items and send WhatsApp alerts.
        Returns number of alerts sent.
        """
        sent_count = 0

        try:
            pending_dir = Path(VAULT_PATH) / "Pending_Approval"
            if not pending_dir.exists():
                return 0

            # Scan all subdirectories for pending items
            for item in pending_dir.rglob('*.md'):
                filename = item.name
                if self._is_in_cooldown(filename, 'approvals'):
                    continue

                # Read first few lines for context
                try:
                    content = item.read_text(encoding='utf-8')[:500]
                except Exception:
                    content = ""

                # Extract type from frontmatter if available
                item_type = "Unknown"
                for line in content.split('\n'):
                    if line.startswith('type:'):
                        item_type = line.split(':', 1)[1].strip()
                        break

                relative_path = item.relative_to(pending_dir)
                message = (
                    f"Approval Required\n\n"
                    f"Item: {filename}\n"
                    f"Type: {item_type}\n"
                    f"Folder: {relative_path.parent}\n"
                    f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
                    f"Please review in Obsidian vault."
                )

                if self._send_whatsapp(message):
                    self._mark_notified(filename, 'approvals')
                    sent_count += 1

            self.state['last_approval_check'] = datetime.now().isoformat()
            self._save_state()

        except Exception as e:
            self.logger.error(f"Approval alert check failed: {e}")

        return sent_count

    def send_daily_summary(self) -> bool:
        """
        Send a daily summary: pending approvals + overdue count + outstanding total.
        Returns True if sent.
        """
        # Check if we already sent a summary today
        last_summary = self.state.get('last_daily_summary')
        if last_summary:
            try:
                last_dt = datetime.fromisoformat(last_summary)
                if last_dt.date() == datetime.now().date():
                    self.logger.info("Daily summary already sent today")
                    return False
            except Exception:
                pass

        # Count pending approvals
        pending_count = 0
        pending_dir = Path(VAULT_PATH) / "Pending_Approval"
        if pending_dir.exists():
            pending_count = sum(1 for _ in pending_dir.rglob('*.md'))

        # Get overdue invoice info from Odoo
        overdue_count = 0
        outstanding_total = 0.0

        try:
            result = ODOO_MCP.post('get_invoices', {
                "state": "posted",
                "payment_state": "not_paid"
            })

            if result.get('success'):
                invoices = result.get('invoices', [])
                for inv in invoices:
                    outstanding_total += inv.get('amount_total', 0)
                    due_date = inv.get('invoice_date_due', '')
                    if due_date:
                        try:
                            due = datetime.fromisoformat(due_date)
                            if due < datetime.now():
                                overdue_count += 1
                        except Exception:
                            pass
        except Exception as e:
            self.logger.warning(f"Could not fetch Odoo data for summary: {e}")

        message = (
            f"Daily Summary - {datetime.now().strftime('%Y-%m-%d')}\n\n"
            f"Pending Approvals: {pending_count}\n"
            f"Overdue Invoices: {overdue_count}\n"
            f"Outstanding Total: ${outstanding_total:,.2f}\n\n"
            f"Have a productive day!"
        )

        if self._send_whatsapp(message):
            self.state['last_daily_summary'] = datetime.now().isoformat()
            self._save_state()
            return True

        return False

    def run_notification_cycle(self) -> dict:
        """
        Run a single notification cycle combining reminders + alerts.
        Returns summary of actions taken.
        """
        self.logger.info("Starting notification cycle")

        reminders_sent = self.check_and_send_payment_reminders()
        alerts_sent = self.check_and_send_approval_alerts()

        # Send daily summary if not sent today
        summary_sent = self.send_daily_summary()

        result = {
            "timestamp": datetime.now().isoformat(),
            "payment_reminders_sent": reminders_sent,
            "approval_alerts_sent": alerts_sent,
            "daily_summary_sent": summary_sent
        }

        self.logger.info(f"Notification cycle complete: {result}")
        return result

    def notify_cloud_health_issue(self, message: str) -> bool:
        """
        Send a WhatsApp alert when the cloud agent has health issues.
        Called by Local agent when it detects a health_alert signal.

        Args:
            message: Health issue description.

        Returns:
            True if notification sent.
        """
        alert = (
            f"Cloud Health Alert\n\n"
            f"{message}\n\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
            f"Please check cloud services."
        )
        return self._send_whatsapp(alert)

    def run(self):
        """Run the notification service continuously"""
        self.logger.info(
            f"WhatsApp Notification Service starting "
            f"(poll interval: {self.poll_interval}s, cooldown: {self.cooldown_hours}h)"
        )

        while True:
            try:
                self.run_notification_cycle()
            except Exception as e:
                self.logger.error(f"Notification cycle error: {e}")

            time.sleep(self.poll_interval)


# ==================== STANDALONE RUNNER ====================

def main():
    """Run the WhatsApp notification service as a standalone process"""
    # Load phone from .env
    phone = None
    env_file = Path(__file__).parent / '.env'
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('WHATSAPP_NOTIFICATION_PHONE='):
                    phone = line.split('=', 1)[1].strip().strip('"').strip("'")

    poll_interval = int(os.getenv('NOTIFICATION_POLL_INTERVAL', '300'))

    print("=" * 60)
    print("WhatsApp Notification Service")
    print("=" * 60)
    print(f"Phone: {phone or 'using MCP default'}")
    print(f"Poll interval: {poll_interval}s")
    print(f"Vault: {VAULT_PATH}")
    print(f"State file: {STATE_FILE}")
    print("=" * 60)

    service = WhatsAppNotificationService(
        poll_interval=poll_interval,
        phone=phone
    )
    service.run()


if __name__ == '__main__':
    main()
