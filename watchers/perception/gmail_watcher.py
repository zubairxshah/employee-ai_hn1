"""
Gmail Watcher Implementation
Monitors Gmail for important/unread messages and creates action files
Enhanced with Odoo invoice workflow integration
"""

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from base_watcher import BaseWatcher
from datetime import datetime
import os
import sys
from pathlib import Path

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class GmailWatcher(BaseWatcher):
    def __init__(self, vault_path: str, credentials_path: str, enable_invoice_workflow: bool = True):
        super().__init__(vault_path, check_interval=120)
        self.creds = Credentials.from_authorized_user_file(credentials_path)
        self.service = build('gmail', 'v1', credentials=self.creds)
        self.processed_ids = set()
        self.enable_invoice_workflow = enable_invoice_workflow
        
        # Load already processed messages from state file
        self.state_file = os.path.join(vault_path, "Logs", "gmail_state.json")
        self._load_state()

    def _load_state(self):
        """Load processed message IDs from state file"""
        import json
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    self.processed_ids = set(state.get('processed_ids', []))
        except Exception as e:
            print(f"[WARN] Failed to load Gmail state: {e}")

    def _save_state(self):
        """Save processed message IDs to state file"""
        import json
        try:
            Path(os.path.dirname(self.state_file)).mkdir(parents=True, exist_ok=True)
            with open(self.state_file, 'w') as f:
                json.dump({'processed_ids': list(self.processed_ids)}, f)
        except Exception as e:
            print(f"[WARN] Failed to save Gmail state: {e}")

    def check_for_updates(self) -> list:
        """Check for new unread important messages"""
        try:
            results = self.service.users().messages().list(
                userId='me', q='is:unread', maxResults=50
            ).execute()
            messages = results.get('messages', [])
            
            # Filter out already processed
            new_messages = [m for m in messages if m['id'] not in self.processed_ids]
            
            # Also check for invoice-related emails specifically
            if self.enable_invoice_workflow:
                invoice_results = self.service.users().messages().list(
                    userId='me', q='subject:invoice OR subject:payment OR subject:invoice', 
                    maxResults=20
                ).execute()
                invoice_messages = invoice_results.get('messages', [])
                
                for msg in invoice_messages:
                    if msg['id'] not in self.processed_ids and msg not in new_messages:
                        new_messages.append(msg)
            
            return new_messages
        except Exception as e:
            print(f"[ERROR] Gmail check failed: {e}")
            return []

    def get_full_message(self, message_id: str) -> dict:
        """Get full message details including body"""
        try:
            msg = self.service.users().messages().get(
                userId='me', id=message_id, format='full'
            ).execute()
            
            # Extract headers
            headers = {h['name']: h['value'] for h in msg['payload']['headers']}
            
            # Extract body
            body = ''
            if 'parts' in msg['payload']:
                for part in msg['payload']['parts']:
                    if part['mimeType'] == 'text/plain' and 'data' in part:
                        import base64
                        body = base64.urlsafe_b64decode(part['data']).decode('utf-8')
                        break
                    elif part['mimeType'] == 'text/html' and 'data' in part:
                        import base64
                        from html2text import html2text
                        html_body = base64.urlsafe_b64decode(part['data']).decode('utf-8')
                        body = html2text(html_body)
                        break
            elif 'body' in msg['payload'] and 'data' in msg['payload']['body']:
                import base64
                body = base64.urlsafe_b64decode(msg['payload']['body']['data']).decode('utf-8')
            
            return {
                'id': msg['id'],
                'headers': headers,
                'body': body,
                'snippet': msg.get('snippet', '')
            }
        except Exception as e:
            print(f"[ERROR] Failed to get message {message_id}: {e}")
            return None

    def process_invoice_email(self, message_data: dict) -> bool:
        """Process email through invoice workflow"""
        try:
            from email_to_invoice_workflow import process_email_message
            
            result = process_email_message(
                message_id=message_data['id'],
                email_content=message_data['body'],
                email_headers=message_data['headers']
            )
            
            if result.get('success'):
                print(f"[OK] Invoice workflow completed")
                if result.get('requires_approval'):
                    print(f"    Approval Request ID: {result.get('approval_request_id')}")
                else:
                    print(f"    Invoice ID: {result.get('invoice_id')} (auto-confirmed)")
                return True
            else:
                print(f"[WARN] Invoice workflow failed: {result.get('error')}")
                return False
                
        except ImportError:
            print(f"[WARN] Invoice workflow module not available")
            return False
        except Exception as e:
            print(f"[ERROR] Invoice workflow error: {e}")
            return False

    def create_action_file(self, message) -> Path:
        """Create action file for manual review or auto-process"""
        message_data = self.get_full_message(message['id'])
        
        if not message_data:
            return None

        # Check if this looks like an invoice email
        subject = message_data['headers'].get('Subject', '').lower()
        is_invoice_email = any(keyword in subject for keyword in [
            'invoice', 'payment', 'bill', 'receipt', 'amount due'
        ])

        # Auto-process invoice emails
        if self.enable_invoice_workflow and is_invoice_email:
            print(f"\n{'='*60}")
            print(f"[INVOICE EMAIL] Detected: {message_data['headers'].get('Subject', 'N/A')}")
            print(f"{'='*60}")
            
            success = self.process_invoice_email(message_data)
            
            if success:
                # Mark as processed
                self.processed_ids.add(message['id'])
                self._save_state()
                
                # Mark email as read
                try:
                    self.service.users().messages().modify(
                        userId='me', id=message['id'], body={'removeLabelIds': ['UNREAD']}
                    ).execute()
                except Exception as e:
                    print(f"[WARN] Failed to mark as read: {e}")
                
                return None  # No action file needed, auto-processed

        # Create action file for non-invoice emails
        content = f'''---
type: email
from: {message_data['headers'].get('From', 'Unknown')}
subject: {message_data['headers'].get('Subject', 'No Subject')}
received: {datetime.now().isoformat()}
priority: high
status: pending
---


## Email Content

{message_data['body'][:2000] if message_data['body'] else message_data['snippet']}


## Suggested Actions
- [ ] Reply to sender
- [ ] Forward to relevant party
- [ ] Archive after processing
- [ ] Create invoice (if applicable)
'''
        filepath = self.needs_action / f'EMAIL_{message["id"]}.md'
        filepath.write_text(content)
        self.processed_ids.add(message['id'])
        self._save_state()
        return filepath


# Example usage
if __name__ == "__main__":
    # This would be configured with actual paths
    vault_path = r"D:\prompteng\AI_Employee_Vault"
    credentials_path = r"D:\prompteng\gmail_credentials.json"  # This would need to be set up separately

    # Only run if credentials exist
    if os.path.exists(credentials_path):
        watcher = GmailWatcher(vault_path, credentials_path, enable_invoice_workflow=True)
        print("Starting Gmail Watcher with Invoice Workflow...")
        watcher.run()
    else:
        print("Gmail credentials not found. Please set up OAuth2 credentials.")
        print("\nTo enable invoice workflow:")
        print("1. Set up Gmail OAuth2 credentials")
        print("2. Place credentials at:", credentials_path)
        print("3. Run this script again")