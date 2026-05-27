"""
Test the complete WhatsApp + Email workflow
Creates an approval request and shows the full flow
"""

import os
import time
from pathlib import Path

VAULT_PATH = r"D:\prompteng\AI_Employee_Vault"
PENDING_DIR = os.path.join(VAULT_PATH, "Pending_Approval")

print("=" * 70)
print("   Complete Workflow Test: WhatsApp + Email")
print("=" * 70)

# Create test approval request
approval_content = """---
type: approval_request
action: send_email
amount: $100.00
recipient: emaxis.newsletter@gmail.com
reason: WhatsApp integration test
created: 2026-02-22T15:30:00
---

## Request Details
- Action: send_email
- Amount: $100.00
- Recipient: emaxis.newsletter@gmail.com
- Reason: WhatsApp integration test

## To Approve
Move this file to Approved folder.
"""

# Ensure Pending_Approval directory exists
os.makedirs(PENDING_DIR, exist_ok=True)

# Create approval file
filename = f"APPROVAL_TEST_{int(time.time())}.md"
filepath = os.path.join(PENDING_DIR, filename)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(approval_content)

print(f"\n[STEP 1] Created approval request:")
print(f"       File: {filename}")
print(f"       Location: Pending_Approval/")
print(f"       Amount: $100.00")
print(f"       Recipient: emaxis.newsletter@gmail.com")

print("\n[STEP 2] Workflow executor should detect this within 5 seconds...")
print("         - WhatsApp notification will be sent")
print("         - Check your WhatsApp for notification")

print("\n" + "=" * 70)
print("WHAT TO EXPECT:")
print("=" * 70)
print("""
1. WhatsApp Notification (within 5-10 seconds):
   - You'll receive WhatsApp message
   - Shows: Action, Amount, Recipient
   - Ask you to review in Obsidian

2. Your Action:
   - Open Obsidian vault
   - Go to Pending_Approval folder
   - Open the file: APPROVAL_TEST_*.md
   - Review the details
   - Move file to Approved folder

3. Email Sent (within 5-10 seconds after approval):
   - Workflow executor detects approval
   - Sends email to emaxis.newsletter@gmail.com
   - Moves file to Done folder

4. Check Results:
   - WhatsApp: You received notification
   - Email: Check Gmail inbox for test email
   - Vault: File moved from Pending -> Approved -> Done
""")

print("=" * 70)
print("\n[OK] Test approval created!")
print("\nCheck your WhatsApp now for the notification...")
print("File created:", filepath)
