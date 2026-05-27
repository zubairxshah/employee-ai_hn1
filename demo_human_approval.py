"""Simulate human approving by moving the file to Approved folder"""

import os
import shutil

REQUEST_ID = "936149f4-011a-462f-9142-8e38609281a1"

VAULT_PATH = r"D:\prompteng\AI_Employee_Vault"
PENDING_DIR = os.path.join(VAULT_PATH, "Pending_Approval")
APPROVED_DIR = os.path.join(VAULT_PATH, "Approved")

filename = f"APPROVAL_{REQUEST_ID}.md"
pending_file = os.path.join(PENDING_DIR, filename)
approved_file = os.path.join(APPROVED_DIR, filename)

print("=" * 60)
print("STEP 2: Human reviews and approves the request")
print("=" * 60)

# Check if file exists in Pending_Approval
if not os.path.exists(pending_file):
    print(f"\n[ERROR] File not found in Pending_Approval: {pending_file}")
    exit(1)

print(f"\n[OK] Found approval request in Pending_Approval")
print(f"    File: {filename}")

# Ensure Approved directory exists
os.makedirs(APPROVED_DIR, exist_ok=True)

# Move the file (this is what the human does in Obsidian/Windows Explorer)
shutil.move(pending_file, approved_file)

print(f"\n[OK] File moved to Approved folder!")
print(f"    From: {pending_file}")
print(f"    To:   {approved_file}")
print(f"\n    This signals to Claude that the action is approved.")
print(f"    Claude will now execute the email send action...")
