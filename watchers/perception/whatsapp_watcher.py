"""
WhatsApp Watcher Implementation
Monitors WhatsApp Web for messages containing specific keywords
"""

from playwright.sync_api import sync_playwright
from base_watcher import BaseWatcher
from pathlib import Path
import json
from datetime import datetime


class WhatsAppWatcher(BaseWatcher):
    def __init__(self, vault_path: str, session_path: str):
        super().__init__(vault_path, check_interval=30)
        self.session_path = Path(session_path)
        self.keywords = ['urgent', 'asap', 'invoice', 'payment', 'help']

    def check_for_updates(self) -> list:
        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                self.session_path, headless=True
            )
            page = browser.pages[0]
            page.goto('https://web.whatsapp.com')
            page.wait_for_selector('[data-testid="chat-list"]')

            # Find unread messages
            unread = page.query_selector_all('[aria-label*="unread"]')
            messages = []
            for chat in unread:
                text = chat.inner_text().lower()
                if any(kw in text for kw in self.keywords):
                    messages.append({'text': text, 'chat': chat})
            browser.close()
            return messages

    def create_action_file(self, message) -> Path:
        content = f'''---
type: whatsapp_message
keywords_found: {", ".join([kw for kw in self.keywords if kw in message['text']])}
received: {datetime.now().isoformat()}
priority: high
status: pending
---


## Message Preview
{message['text']}


## Suggested Actions
- [ ] Review full message
- [ ] Respond appropriately
- [ ] Take necessary action
'''
        # Generate a unique filename based on timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = self.needs_action / f'WHATSAPP_{timestamp}.md'
        filepath.write_text(content)
        return filepath


# Example usage
if __name__ == "__main__":
    vault_path = r"D:\prompteng\AI_Employee_Vault"
    session_path = r"D:\prompteng\whatsapp_session"  # This would need to be set up separately
    
    watcher = WhatsAppWatcher(vault_path, session_path)
    watcher.run()