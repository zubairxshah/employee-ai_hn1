"""Simulate Claude executing the approved action and moving file to Done"""

import os
import shutil

REQUEST_ID = "936149f4-011a-462f-9142-8e38609281a1"

VAULT_PATH = r"D:\prompteng\AI_Employee_Vault"
APPROVED_DIR = os.path.join(VAULT_PATH, "Approved")
DONE_DIR = os.path.join(VAULT_PATH, "Done")

filename = f"APPROVAL_{REQUEST_ID}.md"
approved_file = os.path.join(APPROVED_DIR, filename)
done_file = os.path.join(DONE_DIR, filename)

print("=" * 60)
print("STEP 4: Claude executes the approved action")
print("=" * 60)

# Check if file exists in Approved
if not os.path.exists(approved_file):
    print(f"\n[ERROR] File not found in Approved: {approved_file}")
    exit(1)

print(f"\n[OK] Found approved file in Approved folder")
print(f"    File: {filename}")

# Simulate Claude executing the action (sending email)
print(f"\n[ACTION] Executing: send_email")
print(f"         To: client.a@email.com")
print(f"         Subject: Invoice #TEST-001 - February 2026")
print(f"         Amount: $2,500.00")
print(f"         Status: Email sent successfully!")

# Ensure Done directory exists
os.makedirs(DONE_DIR, exist_ok=True)

# Move the file to Done (task completed)
shutil.move(approved_file, done_file)

print(f"\n[OK] Task completed! File moved to Done folder.")
print(f"    From: {approved_file}")
print(f"    To:   {done_file}")

print("\n" + "=" * 60)
print("WORKFLOW COMPLETE!")
print("=" * 60)
print("""
Summary:
  1. File watcher detected task in Inbox -> moved to Needs_Action
  2. Claude analyzed task, determined approval needed (> $500)
  3. Claude created approval request in Pending_Approval
  4. Human reviewed and moved file to Approved
  5. Claude detected approval, executed email send
  6. Claude moved file to Done

The complete human-in-the-loop workflow is now demonstrated!
""")
