"""
Gmail Watcher Skill
Monitors Gmail for important/unread messages and creates action files
"""

import os
import base64
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List

from .. import AgentSkill


class GmailWatcherSkill(AgentSkill):
    """
    Skill for monitoring Gmail and processing important messages.
    
    Capabilities:
    - Monitors Gmail for important/unread messages
    - Filters for messages marked as important
    - Creates action files with email content
    - Tracks processed messages to avoid duplicates
    
    Configuration:
    - credentials_path: Path to Gmail OAuth2 credentials
    - labels_to_monitor: List of Gmail labels to monitor
    - max_results: Maximum number of emails to fetch per scan
    - processed_messages_log: File to track processed message IDs
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        config = config or {}
        config.setdefault('labels_to_monitor', ['INBOX', 'IMPORTANT'])
        config.setdefault('max_results', 10)
        config.setdefault('processed_messages_log', 'processed_gmail.txt')
        super().__init__(config)
        
        self.processed_messages = set()
        self._load_processed_messages()
        self._service = None
    
    def _load_processed_messages(self):
        """Load list of already processed message IDs"""
        log_path = Path(self.config.get('processed_messages_log', 'processed_gmail.txt'))
        if log_path.exists():
            try:
                with open(log_path, 'r') as f:
                    self.processed_messages = set(line.strip() for line in f)
            except Exception:
                self.processed_messages = set()
    
    def _save_processed_messages(self):
        """Save list of processed message IDs"""
        log_path = Path(self.config.get('processed_messages_log', 'processed_gmail.txt'))
        try:
            with open(log_path, 'w') as f:
                for msg_id in self.processed_messages:
                    f.write(f"{msg_id}\n")
        except Exception as e:
            self.logger.warning(f"Could not save processed messages log: {e}")
    
    def _get_credentials(self):
        """Get Gmail API credentials"""
        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            
            # Check for token file
            token_file = Path(__file__).parent.parent.parent / '.gmail_token.json'
            credentials_file = Path(__file__).parent.parent.parent / 'gmail_credentials.json'
            
            # Use provided path or defaults
            credentials_path = self.config.get('credentials_path', str(credentials_file))
            token_path = self.config.get('token_path', str(token_file))
            
            creds = None
            
            # Load existing token
            if Path(token_path).exists():
                creds = Credentials.from_authorized_user_file(token_path, self._get_scopes())
            
            # Refresh if expired
            if creds and creds.expired:
                if creds.refresh_token:
                    creds.refresh(Request())
                    # Save refreshed token
                    with open(token_path, 'w') as f:
                        f.write(creds.to_json())
                else:
                    creds = None
            
            return creds
            
        except ImportError:
            self.logger.error("Google API libraries not installed")
            return None
        except Exception as e:
            self.logger.error(f"Error loading credentials: {e}")
            return None
    
    def _get_scopes(self):
        """Get Gmail API scopes"""
        return [
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/gmail.modify'
        ]
    
    def _get_service(self):
        """Get Gmail API service"""
        if self._service:
            return self._service
        
        creds = self._get_credentials()
        if not creds:
            return None
        
        try:
            from googleapiclient.discovery import build
            self._service = build('gmail', 'v1', credentials=creds)
            return self._service
        except Exception as e:
            self.logger.error(f"Error building Gmail service: {e}")
            return None
    
    def validate_inputs(self, parameters: Dict[str, Any]) -> tuple:
        """Validate input parameters"""
        if 'vault_path' not in parameters:
            return False, "Missing required parameter: vault_path"
        
        return True, ""
    
    def get_capability_description(self) -> str:
        """Return skill description"""
        return (
            f"Gmail Watcher Skill (v{self.version}): "
            f"Monitors Gmail for important messages and creates action files. "
            f"Labels: {', '.join(self.config.get('labels_to_monitor', []))}"
        )
    
    def _decode_body(self, message: Dict) -> str:
        """Decode email body from Gmail API format"""
        try:
            if 'payload' not in message:
                return ""
            
            payload = message['payload']
            
            # Try to find body in parts
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain' and 'body' in part:
                        data = part['body'].get('data', '')
                        if data:
                            return base64.urlsafe_b64decode(data).decode('utf-8')
                    elif part['mimeType'] == 'text/html' and 'body' in part:
                        data = part['body'].get('data', '')
                        if data:
                            return base64.urlsafe_b64decode(data).decode('utf-8')
            
            # Try main body
            if 'body' in payload and 'data' in payload['body']:
                data = payload['body']['data']
                return base64.urlsafe_b64decode(data).decode('utf-8')
            
            return ""
        except Exception as e:
            self.logger.error(f"Error decoding email body: {e}")
            return ""
    
    def _extract_headers(self, headers: List[Dict]) -> Dict[str, str]:
        """Extract email headers into a dictionary"""
        return {h['name']: h['value'] for h in headers}
    
    def _create_action_file(self, email_data: Dict, vault_path: Path) -> Path:
        """Create action file for an email"""
        needs_action_dir = vault_path / 'Needs_Action'
        needs_action_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename
        subject = email_data.get('subject', 'No Subject')
        safe_subject = "".join(c if c.isalnum() else '_' for c in subject)[:50]
        filename = f"EMAIL_{safe_subject}_{email_data.get('id', 'unknown')[:8]}.md"
        filepath = needs_action_dir / filename
        
        content = f"""---
type: email
priority: {'high' if email_data.get('important') else 'normal'}
from: {email_data.get('from', 'unknown')}
to: {email_data.get('to', 'unknown')}
subject: {subject}
received: {email_data.get('date', datetime.now().isoformat())}
message_id: {email_data.get('id', 'unknown')}
status: new
---

# Email: {subject}

## From
{email_data.get('from', 'unknown')}

## To
{email_data.get('to', 'unknown')}

## Date
{email_data.get('date', 'unknown')}

## Body
{email_data.get('body', 'No content available')}

## Attachments
{', '.join(email_data.get('attachments', [])) or 'None'}

## Suggested Action
Review and respond as needed according to company handbook.

## Company Handbook Rules
- Respond to important emails within 24 hours
- Escalate urgent matters to human
- Log all communications
"""
        
        filepath.write_text(content, encoding='utf-8')
        return filepath
    
    def _fetch_emails(self) -> List[Dict]:
        """Fetch emails from Gmail API"""
        service = self._get_service()
        if not service:
            return []
        
        try:
            # Build query for important unread emails
            query = 'is:unread is:important'
            
            results = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=self.config.get('max_results', 10)
            ).execute()
            
            messages = results.get('messages', [])
            emails = []
            
            for msg in messages:
                msg_id = msg['id']
                
                # Skip already processed
                if msg_id in self.processed_messages:
                    continue
                
                # Get full message details
                message = service.users().messages().get(
                    userId='me',
                    id=msg_id,
                    format='full'
                ).execute()
                
                # Extract data
                headers = self._extract_headers(message['payload'].get('headers', []))
                body = self._decode_body(message)
                
                email_data = {
                    'id': msg_id,
                    'from': headers.get('From', 'Unknown'),
                    'to': headers.get('To', 'Unknown'),
                    'subject': headers.get('Subject', 'No Subject'),
                    'date': headers.get('Date', datetime.now().isoformat()),
                    'body': body,
                    'important': 'IMPORTANT' in message.get('labelIds', []),
                    'attachments': [],
                    'snippet': message.get('snippet', '')
                }
                
                # Check for attachments
                if 'parts' in message['payload']:
                    for part in message['payload']['parts']:
                        if 'filename' in part and part['filename']:
                            email_data['attachments'].append(part['filename'])
                
                emails.append(email_data)
            
            return emails
            
        except Exception as e:
            self.logger.error(f"Error fetching emails: {e}")
            return []
    
    def execute(self, context: Dict[str, Any], parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the Gmail watcher skill.
        
        Parameters:
        - vault_path: Path to the Obsidian vault
        - scan: If True, scan immediately; if False, return watcher info
        
        Returns:
        - Dictionary with scan results or watcher information
        """
        vault_path = Path(parameters['vault_path'])
        scan = parameters.get('scan', True)
        
        if not scan:
            # Return watcher info without scanning
            return {
                "success": True,
                "watcher_info": {
                    "labels_monitored": self.config.get('labels_to_monitor', []),
                    "max_results": self.config.get('max_results', 10),
                    "processed_count": len(self.processed_messages),
                    "credentials_configured": self.config.get('credentials_path') is not None
                }
            }
        
        # Check if we have credentials
        creds = self._get_credentials()
        if not creds:
            return {
                "success": False,
                "error": "Gmail credentials not configured. Run: python scripts/gmail_auth.py",
                "status": "credentials_required"
            }
        
        # Fetch and process emails
        try:
            emails = self._fetch_emails()
            
            new_emails = []
            processed_count = 0
            
            for email in emails:
                msg_id = email.get('id')
                
                # Create action file
                try:
                    action_file = self._create_action_file(email, vault_path)
                    
                    # Mark as processed
                    self.processed_messages.add(msg_id)
                    self._save_processed_messages()
                    
                    new_emails.append({
                        "id": msg_id,
                        "subject": email.get('subject'),
                        "from": email.get('from'),
                        "action_file": str(action_file)
                    })
                    processed_count += 1
                    
                    self.logger.info(f"Processed email: {email.get('subject')}")
                    
                except Exception as e:
                    self.logger.error(f"Error processing email {msg_id}: {e}")
            
            return {
                "success": True,
                "emails_processed": processed_count,
                "new_emails": new_emails,
                "total_processed_all_time": len(self.processed_messages)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "status": "fetch_failed"
            }


# Auto-register the skill when module is imported
def _register():
    from ..registry import register_skill
    register_skill(GmailWatcherSkill, "gmail_watcher")

_register()
