2. Architecture: Perception → Reasoning → Action
A. Perception (The "Watchers")
Since Claude Code can't "listen" to the internet 24/7, you use lightweight Python Sentinel Scripts running in the background:
Comms Watcher: Monitors Gmail and WhatsApp (via local web-automation or APIs) and saves new urgent messages as .md files in a /Needs_Action folder.
Finance Watcher: Downloads local CSVs or calls banking APIs to log new transactions in /Accounting/Current_Month.md.
It will also be able to run on your laptop and immediately “wake up” as soon as you open your machine.
Watcher Architecture
The Watcher layer is your AI Employee's sensory system. These lightweight Python scripts run continuously, monitoring various inputs and creating actionable files for Claude to process.
Core Watcher Pattern
All Watchers follow this structure:
# base_watcher.py - Template for all watchers
import time
import logging
from pathlib import Path
from abc import ABC, abstractmethod


class BaseWatcher(ABC):
    def __init__(self, vault_path: str, check_interval: int = 60):
        self.vault_path = Path(vault_path)
        self.needs_action = self.vault_path / 'Needs_Action'
        self.check_interval = check_interval
        self.logger = logging.getLogger(self.__class__.__name__)
        
    @abstractmethod
    def check_for_updates(self) -> list:
        '''Return list of new items to process'''
        pass
    
    @abstractmethod
    def create_action_file(self, item) -> Path:
        '''Create .md file in Needs_Action folder'''
        pass
    
    def run(self):
        self.logger.info(f'Starting {self.__class__.__name__}')
        while True:
            try:
                items = self.check_for_updates()
                for item in items:
                    self.create_action_file(item)
            except Exception as e:
                self.logger.error(f'Error: {e}')
            time.sleep(self.check_interval)
Gmail Watcher Implementation
# gmail_watcher.py
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from base_watcher import BaseWatcher
from datetime import datetime


class GmailWatcher(BaseWatcher):
    def __init__(self, vault_path: str, credentials_path: str):
        super().__init__(vault_path, check_interval=120)
        self.creds = Credentials.from_authorized_user_file(credentials_path)
        self.service = build('gmail', 'v1', credentials=self.creds)
        self.processed_ids = set()
        
    def check_for_updates(self) -> list:
        results = self.service.users().messages().list(
            userId='me', q='is:unread is:important'
        ).execute()
        messages = results.get('messages', [])
        return [m for m in messages if m['id'] not in self.processed_ids]
    
    def create_action_file(self, message) -> Path:
        msg = self.service.users().messages().get(
            userId='me', id=message['id']
        ).execute()
        
        # Extract headers
        headers = {h['name']: h['value'] for h in msg['payload']['headers']}
        
        content = f'''---
type: email
from: {headers.get('From', 'Unknown')}
subject: {headers.get('Subject', 'No Subject')}
received: {datetime.now().isoformat()}
priority: high
status: pending
---


## Email Content
{msg.get('snippet', '')}


## Suggested Actions
- [ ] Reply to sender
- [ ] Forward to relevant party
- [ ] Archive after processing
'''
        filepath = self.needs_action / f'EMAIL_{message["id"]}.md'
        filepath.write_text(content)
        self.processed_ids.add(message['id'])
        return filepath
WhatsApp Watcher (Playwright-based)
Note: This uses WhatsApp Web automation. Be aware of WhatsApp's terms of service.
# whatsapp_watcher.py
from playwright.sync_api import sync_playwright
from base_watcher import BaseWatcher
from pathlib import Path
import json


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
File System Watcher (for local drops)
# filesystem_watcher.py
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path
import shutil


class DropFolderHandler(FileSystemEventHandler):
    def __init__(self, vault_path: str):
        self.needs_action = Path(vault_path) / 'Needs_Action'
        
    def on_created(self, event):
        if event.is_directory:
            return
        source = Path(event.src_path)
        dest = self.needs_action / f'FILE_{source.name}'
        shutil.copy2(source, dest)
        self.create_metadata(source, dest)
        
    def create_metadata(self, source: Path, dest: Path):
        meta_path = dest.with_suffix('.md')
        meta_path.write_text(f'''---
type: file_drop
original_name: {source.name}
size: {source.stat().st_size}
---


New file dropped for processing.
''')


B. Reasoning (Claude Code)
When the Watcher detects a change, it triggers a Claude command:
Read: "Check /Needs_Action and /Accounting."
Think: "I see a WhatsApp message from a client asking for an invoice and a bank transaction showing a late payment fee."
Plan: Claude creates a Plan.md in Obsidian with checkboxes for the next steps.
C. Action (The "Hands")
Model Context Protocol (MCP) servers are Claude Code's hands for interacting with external systems. Each MCP server exposes specific capabilities that Claude can invoke.
Claude uses custom MCP (Model Context Protocol) servers to act:
WhatsApp/Social MCP: To send the reply or post the scheduled update.
Browser/Payment MCP: To log into a payment portal, draft a payment, and stop.
Human-in-the-Loop (HITL): Claude writes a file: APPROVAL_REQUIRED_Payment_Client_A.md. It will not click "Send" until you move that file to the /Approved folder.
Recommended MCP Servers
Server
Capabilities
Use Case
filesystem
Read, write, list files
Built-in, use for vault
email-mcp
Send, draft, search emails
Gmail integration
browser-mcp
Navigate, click, fill forms
Payment portals
calendar-mcp
Create, update events
Scheduling
slack-mcp
Send messages, read channels
Team communication


Claude Code Configuration
Configure MCP servers in your Claude Code settings:
// ~/.config/claude-code/mcp.json
{
  "servers": [
    {
      "name": "email",
      "command": "node",
      "args": ["/path/to/email-mcp/index.js"],
      "env": {
        "GMAIL_CREDENTIALS": "/path/to/credentials.json"
      }
    },
    {
      "name": "browser",
      "command": "npx",
      "args": ["@anthropic/browser-mcp"],
      "env": {
        "HEADLESS": "true"
      }
    }
  ]
}
Human-in-the-Loop Pattern
For sensitive actions, Claude writes an approval request file instead of acting directly:
# When Claude detects a sensitive action needed:
# 1. Create approval request file


# /Vault/Pending_Approval/PAYMENT_Client_A_2026-01-07.md
---
type: approval_request
action: payment
amount: 500.00
recipient: Client A
reason: Invoice #1234 payment
created: 2026-01-07T10:30:00Z
expires: 2026-01-08T10:30:00Z
status: pending
---


## Payment Details
- Amount: $500.00
- To: Client A (Bank: XXXX1234)
- Reference: Invoice #1234


## To Approve
Move this file to /Approved folder.


## To Reject
Move this file to /Rejected folder.
The Orchestrator watches the /Approved folder and triggers the actual MCP action when files appear.
D. Persistence (The "Ralph Wiggum" Loop)
Claude Code runs in interactive mode - after processing a prompt, it waits for more input.
To keep your AI Employee working autonomously until a task is complete, use the
Ralph Wiggum pattern: a Stop hook that intercepts Claude's exit and feeds the prompt back.

How Does It Work?

Orchestrator creates state file with prompt
Claude works on task
Claude tries to exit
Stop hook checks: Is task file in /Done?
YES → Allow exit (complete)
NO → Block exit, re-inject prompt, and allow Claude to see its own previous failed output (loop continues).
Repeat until complete or max iterations

Usage

  ```bash
  # Start a Ralph loop
  /ralph-loop "Process all files in /Needs_Action, move to /Done when complete" \
    --completion-promise "TASK_COMPLETE" \
    --max-iterations 10
```

Two Completion Strategies:
Promise-based (simple): Claude outputs `<promise>TASK_COMPLETE</promise>`
File movement (advanced - Gold tier): Stop hook detects when task file moves to /Done
More reliable (completion is natural part of workflow)
Orchestrator creates state file programmatically
See reference implementation for details

Reference: https://github.com/anthropics/claude-code/tree/main/.claude/plugins/ralph-wiggum

3. Continuous vs. Scheduled Operations
Operation Type
Example Task
Local Trigger
Scheduled
Daily Briefing: Summarize business tasks at 8:00 AM.
cron (Mac/Linux) or Task Scheduler (Win) calls Claude.
Continuous
Lead Capture: Watch WhatsApp for keywords like "Pricing."
Python watchdog script monitoring the /Inbox folder.
Project-Based
Q1 Tax Prep: Categorize 3 months of business expenses.
Manual drag-and-drop of a file into the /Active_Project folder.

