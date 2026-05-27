"""Create a test task file in the Inbox to trigger the file system watcher"""

import os
from datetime import datetime

VAULT_PATH = r"D:\prompteng\AI_Employee_Vault"
INBOX_DIR = os.path.join(VAULT_PATH, "Inbox")

# Ensure Inbox exists
os.makedirs(INBOX_DIR, exist_ok=True)

# Create test task file
task_content = """---
type: task
source: manual_test
created: 2026-02-22T14:00:00
priority: high
status: new
---

# Test Invoice Task - Client A

## Task Description
Process and send invoice #TEST-001 to Client A for February 2026 work.

## Details
- **Client:** Client A
- **Email:** client.a@email.com
- **Invoice Number:** TEST-001
- **Period:** February 2026
- **Hours:** 25 hours
- **Rate:** $100/hour
- **Total Amount:** $2,500.00
- **Due Date:** March 22, 2026

## Suggested Actions
1. Generate invoice PDF
2. Create email draft with invoice attached
3. Request human approval (amount > $500)
4. Send email after approval
5. Log transaction in accounting

## Notes
This is a TEST task to demonstrate the file system watcher and approval workflow.
"""

# Write the file
task_file = os.path.join(INBOX_DIR, "test_invoice_task.md")
with open(task_file, 'w', encoding='utf-8') as f:
    f.write(task_content)

print(f"[OK] Test task file created: {task_file}")
print(f"       File watcher should detect this and move it to Needs_Action...")
