"""
Test File Watcher Fix
Verifies that files in Approved/Rejected don't get moved to Needs_Action
"""

import os
import time
from pathlib import Path

VAULT_PATH = r"D:\prompteng\AI_Employee_Vault"
INBOX_DIR = os.path.join(VAULT_PATH, "Inbox")
APPROVED_DIR = os.path.join(VAULT_PATH, "Approved")
REJECTED_DIR = os.path.join(VAULT_PATH, "Rejected")
NEEDS_ACTION_DIR = os.path.join(VAULT_PATH, "Needs_Action")

print("=" * 70)
print("   FILE WATCHER FIX TEST")
print("=" * 70)

# Test 1: Create file in Inbox (SHOULD be moved to Needs_Action)
print("\nTEST 1: File in Inbox (should be moved to Needs_Action)")
print("-" * 70)

inbox_file = os.path.join(INBOX_DIR, f"TEST_INBOX_{int(time.time())}.md")
with open(inbox_file, 'w') as f:
    f.write("# Test Inbox File\n\nThis should be moved to Needs_Action/")

print(f"Created: {inbox_file}")
print("Waiting 5 seconds for watcher...")
time.sleep(5)

if os.path.exists(inbox_file):
    print("[FAIL] File still in Inbox (watcher not working)")
elif os.path.exists(os.path.join(NEEDS_ACTION_DIR, os.path.basename(inbox_file))):
    print("[OK] File moved to Needs_Action (watcher working!)")
else:
    print("[WARN] File disappeared from both locations")

# Test 2: Create file in Approved (should NOT be moved)
print("\nTEST 2: File in Approved (should NOT be moved)")
print("-" * 70)

approved_file = os.path.join(APPROVED_DIR, f"TEST_APPROVED_{int(time.time())}.md")
with open(approved_file, 'w') as f:
    f.write("# Test Approved File\n\nThis should STAY in Approved/")

print(f"Created: {approved_file}")
print("Waiting 5 seconds...")
time.sleep(5)

if os.path.exists(approved_file):
    print("[OK] File still in Approved (correct!)")
else:
    print("[FAIL] File was moved (watcher still broken)")
    # Check where it went
    for dirname in ["Needs_Action", "Done", "Rejected"]:
        check_path = os.path.join(VAULT_PATH, dirname, os.path.basename(approved_file))
        if os.path.exists(check_path):
            print(f"       File found in: {dirname}/")

# Test 3: Create file in Rejected (should NOT be moved)
print("\nTEST 3: File in Rejected (should NOT be moved)")
print("-" * 70)

rejected_file = os.path.join(REJECTED_DIR, f"TEST_REJECTED_{int(time.time())}.md")
with open(rejected_file, 'w') as f:
    f.write("# Test Rejected File\n\nThis should STAY in Rejected/")

print(f"Created: {rejected_file}")
print("Waiting 5 seconds...")
time.sleep(5)

if os.path.exists(rejected_file):
    print("[OK] File still in Rejected (correct!)")
else:
    print("[FAIL] File was moved (watcher still broken)")
    # Check where it went
    for dirname in ["Needs_Action", "Done", "Approved"]:
        check_path = os.path.join(VAULT_PATH, dirname, os.path.basename(rejected_file))
        if os.path.exists(check_path):
            print(f"       File found in: {dirname}/")

# Summary
print("\n" + "=" * 70)
print("   TEST SUMMARY")
print("=" * 70)
print("""
Expected Behavior:
  - Inbox files → Moved to Needs_Action [TESTED]
  - Approved files → Stay in Approved [TESTED]
  - Rejected files → Stay in Rejected [TESTED]

If all tests passed, the watcher fix is working!
""")
print("=" * 70)
