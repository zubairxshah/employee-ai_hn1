"""
LinkedIn Watcher
Monitors LinkedIn for new messages/leads and creates action files.

Dual mode:
  1. API-based: Uses LinkedIn MCP /get_messages endpoint
  2. Vault-based fallback: Scans Incoming_LinkedIn/ folder for manually placed files

State persistence via Vault/Logs/linkedin_watcher_state.json
"""

import os
import sys
import json
import requests
from pathlib import Path
from datetime import datetime

# Ensure imports from project root work
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from watchers.perception.base_watcher import BaseWatcher


VAULT_PATH = os.getenv('VAULT_PATH', r'D:\prompteng\AI_Employee_Vault')
LINKEDIN_MCP_URL = 'http://localhost:8002'
STATE_FILE = os.path.join(VAULT_PATH, 'Logs', 'linkedin_watcher_state.json')


class LinkedInWatcher(BaseWatcher):
    """
    Watches for new LinkedIn messages/leads and triggers the
    linkedin_to_customer_workflow for processing.

    Check interval: 120 seconds
    """

    def __init__(self, vault_path: str = VAULT_PATH, check_interval: int = 120):
        super().__init__(vault_path, check_interval)

        self.incoming_dir = self.vault_path / 'Incoming_LinkedIn'
        self.incoming_dir.mkdir(parents=True, exist_ok=True)
        self.needs_action.mkdir(parents=True, exist_ok=True)

        self.processed_ids = set()
        self.processed_files = set()
        self._load_state()

    # ==================== STATE PERSISTENCE ====================

    def _load_state(self):
        """Load processed message IDs from state file"""
        try:
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE, 'r') as f:
                    state = json.load(f)
                    self.processed_ids = set(state.get('processed_ids', []))
                    self.processed_files = set(state.get('processed_files', []))
        except Exception as e:
            self.logger.warning(f"Failed to load LinkedIn watcher state: {e}")

    def _save_state(self):
        """Save processed message IDs to state file"""
        try:
            Path(os.path.dirname(STATE_FILE)).mkdir(parents=True, exist_ok=True)
            with open(STATE_FILE, 'w') as f:
                json.dump({
                    'processed_ids': list(self.processed_ids),
                    'processed_files': list(self.processed_files),
                    'last_check': datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            self.logger.warning(f"Failed to save LinkedIn watcher state: {e}")

    # ==================== CHECK FOR UPDATES ====================

    def check_for_updates(self) -> list:
        """
        Return list of new LinkedIn items to process.
        Tries API mode first, falls back to vault-based mode.
        """
        items = []

        # Mode 1: API-based (LinkedIn MCP /get_messages)
        api_items = self._check_api()
        items.extend(api_items)

        # Mode 2: Vault-based fallback (Incoming_LinkedIn/)
        vault_items = self._check_vault()
        items.extend(vault_items)

        if items:
            self.logger.info(f"Found {len(items)} new LinkedIn item(s)")

        return items

    def _check_api(self) -> list:
        """Check LinkedIn MCP for new messages via API"""
        items = []
        try:
            response = requests.get(
                f"{LINKEDIN_MCP_URL}/get_messages",
                timeout=15
            )

            if response.status_code != 200:
                self.logger.debug(f"LinkedIn MCP returned {response.status_code}")
                return []

            data = response.json()
            messages = data.get('messages', [])

            for msg in messages:
                msg_id = msg.get('id', '')
                if msg_id and msg_id not in self.processed_ids:
                    items.append({
                        'source': 'api',
                        'id': msg_id,
                        'body': msg.get('body', ''),
                        'from': msg.get('from', ''),
                        'created_at': msg.get('created_at', ''),
                    })

        except requests.ConnectionError:
            self.logger.debug("LinkedIn MCP not available, using vault fallback")
        except Exception as e:
            self.logger.warning(f"LinkedIn API check error: {e}")

        return items

    def _check_vault(self) -> list:
        """Check Incoming_LinkedIn/ folder for new files"""
        items = []

        if not self.incoming_dir.exists():
            return []

        for filepath in self.incoming_dir.glob('*.md'):
            filename = filepath.name
            if filename in self.processed_files:
                continue

            try:
                content = filepath.read_text(encoding='utf-8')
                items.append({
                    'source': 'vault',
                    'id': filename,
                    'filepath': str(filepath),
                    'content': content,
                    'filename': filename,
                })
            except Exception as e:
                self.logger.error(f"Failed to read {filepath}: {e}")

        return items

    # ==================== CREATE ACTION FILE ====================

    def create_action_file(self, item) -> Path:
        """
        Create an action file in Needs_Action and trigger the
        linkedin_to_customer_workflow.
        """
        source = item.get('source', 'unknown')
        item_id = item.get('id', 'unknown')

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"LINKEDIN_{item_id}_{timestamp}.md"

        if source == 'api':
            content = self._format_api_message(item)
        else:
            content = self._format_vault_message(item)

        # Write action file
        filepath = self.needs_action / filename
        filepath.write_text(content, encoding='utf-8')

        # Mark as processed
        if source == 'api':
            self.processed_ids.add(item_id)
        else:
            self.processed_files.add(item_id)
        self._save_state()

        self.logger.info(f"Created action file: {filename}")

        # Try to trigger the workflow
        self._trigger_workflow(item_id, item)

        return filepath

    def _format_api_message(self, item: dict) -> str:
        """Format an API message into action file content"""
        return f"""---
type: linkedin_message
source: api
message_id: {item.get('id', '')}
from: {item.get('from', '')}
received: {datetime.now().isoformat()}
status: pending
---

# LinkedIn Message

## From
{item.get('from', 'Unknown')}

## Message
{item.get('body', 'No content')}

## Received
{item.get('created_at', datetime.now().isoformat())}

## Suggested Actions
- [ ] Review message content
- [ ] Add as lead in Odoo
- [ ] Send follow-up response
"""

    def _format_vault_message(self, item: dict) -> str:
        """Format a vault-placed file into action file content"""
        content = item.get('content', '')

        return f"""---
type: linkedin_message
source: vault_import
filename: {item.get('filename', '')}
received: {datetime.now().isoformat()}
status: pending
---

# LinkedIn Message (Imported)

## Original Content
{content}

## Suggested Actions
- [ ] Review message content
- [ ] Add as lead in Odoo
- [ ] Send follow-up response
"""

    def _trigger_workflow(self, message_id: str, message_data: dict):
        """Try to trigger the linkedin_to_customer_workflow"""
        try:
            from linkedin_to_customer_workflow import process_linkedin_message
            result = process_linkedin_message(message_id, message_data)
            self.logger.info(f"Workflow triggered for {message_id}: {result.get('success')}")
        except ImportError:
            self.logger.debug("linkedin_to_customer_workflow not available")
        except Exception as e:
            self.logger.error(f"Workflow trigger failed for {message_id}: {e}")


# ==================== STANDALONE RUNNER ====================

if __name__ == "__main__":
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s %(name)s: %(message)s',
        datefmt='%H:%M:%S'
    )

    vault_path = os.getenv('VAULT_PATH', r'D:\prompteng\AI_Employee_Vault')

    print("=" * 60)
    print("LinkedIn Watcher")
    print("=" * 60)
    print(f"Vault: {vault_path}")
    print(f"LinkedIn MCP: {LINKEDIN_MCP_URL}")
    print(f"Check interval: 120s")
    print(f"Incoming folder: {vault_path}/Incoming_LinkedIn/")
    print("=" * 60)

    watcher = LinkedInWatcher(vault_path)
    watcher.run()
