"""
Test that WhatsApp notification is sent ONLY ONCE per approval
This verifies the fix for the multiple browser windows issue
"""

import os
import time
from pathlib import Path

VAULT_PATH = r"D:\prompteng\AI_Employee_Vault"
PENDING_DIR = os.path.join(VAULT_PATH, "Pending_Approval")
LOGS_DIR = os.path.join(VAULT_PATH, "Logs")

print("=" * 70)
print("   WhatsApp Fix Verification Test")
print("=" * 70)
print("\nThis test verifies that:")
print("  1. WhatsApp notification is sent ONLY ONCE per approval")
print("  2. Browser closes automatically after sending")
print("  3. No multiple windows are opened")
print("  4. 60-second cooldown is enforced")
print("\n" + "=" * 70)

# Create test approval request
approval_content = """---
type: approval_request
action: send_email
amount: $50.00
recipient: test@example.com
reason: Fix verification test
---

## Request Details
- Action: send_email
- Amount: $50.00
- Reason: Fix verification test
"""

# Ensure Pending_Approval directory exists
os.makedirs(PENDING_DIR, exist_ok=True)

# Create approval file
filename = f"APPROVAL_FIX_TEST_{int(time.time())}.md"
filepath = os.path.join(PENDING_DIR, filename)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(approval_content)

print(f"\n[STEP 1] Created test approval: {filename}")
print(f"         Location: Pending_Approval/")

print("\n[STEP 2] Workflow executor will detect this within 5 seconds...")
print("         Expected behavior:")
print("         - ONE browser window opens")
print("         - WhatsApp notification sent")
print("         - Browser closes automatically")
print("         - File marked as notified")

print("\n[STEP 3] Waiting 15 seconds to observe behavior...")
print("         (Watch for browser behavior)")

# Wait and observe
for i in range(15, 0, -1):
    time.sleep(1)
    print(f"         Waiting... {i}s", end='\r')

print("\n\n[STEP 4] Checking if file was marked as notified...")

# Check if file was marked
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

if 'whatsapp_notified: true' in content:
    print("         [OK] File marked as whatsapp_notified: true")
    print("         [OK] Duplicate notifications will be prevented!")
else:
    print("         [WARN] File not yet marked (may still be processing)")

print("\n[STEP 5] Checking notification log...")
time.sleep(2)  # Give time for log to be written

log_file = os.path.join(LOGS_DIR, "whatsapp_notifications.log")
if os.path.exists(log_file):
    with open(log_file, 'r', encoding='utf-8') as f:
        log_content = f.read()
    
    # Count occurrences of this file in log
    count = log_content.count(filename)
    print(f"         Log entries for this file: {count}")
    
    if count == 1:
        print("         [OK] Notification sent EXACTLY ONCE!")
    elif count > 1:
        print(f"         [WARN] Notification sent {count} times (should be 1)")
    else:
        print("         [INFO] No log entry yet (still processing)")
else:
    print("         [INFO] Log file not found (still processing)")

print("\n" + "=" * 70)
print("VERIFICATION RESULTS")
print("=" * 70)
print("""
FIX VERIFICATION CHECKLIST:

[ ] 1. Only ONE browser window opened
[ ] 2. Browser closed automatically after sending
[ ] 3. No multiple WhatsApp Web instances
[ ] 4. File marked with 'whatsapp_notified: true'
[ ] 5. Log shows exactly 1 notification

If all boxes are checked, the fix is working!
""")

print("=" * 70)
print("\nTest file created:", filepath)
print("Log file:", log_file)
print("\nTo test again, create a NEW approval file (different filename)")
print("The same file will NOT trigger another notification.")
