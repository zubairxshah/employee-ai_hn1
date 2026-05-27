"""Verify the approval status changed from pending to approved"""

import requests
import json

REQUEST_ID = "936149f4-011a-462f-9142-8e38609281a1"
MCP_URL = "http://localhost:8003"

print("=" * 60)
print("STEP 3: Claude checks approval status")
print("=" * 60)

# Check approval status
response = requests.post(f"{MCP_URL}/check_approval", json={"request_id": REQUEST_ID})
result = response.json()

print(f"\nApproval Status Check:")
print(json.dumps(result, indent=2))

status = result.get("status")

if status == "approved":
    print(f"\n[OK] Status is 'approved'!")
    print(f"     Claude can now execute the email send action.")
    print(f"     After execution, the file will be moved to Done folder.")
elif status == "rejected":
    print(f"\n[INFO] Status is 'rejected'.")
    print(f"       Claude will NOT execute the action.")
    print(f"       Task will be logged as rejected.")
elif status == "pending":
    print(f"\n[INFO] Status is still 'pending'.")
    print(f"       Waiting for human approval...")
else:
    print(f"\n[INFO] Unknown status: {status}")

# Also list current pending approvals
print("\n" + "=" * 60)
print("Current Pending Approvals:")
print("=" * 60)

response = requests.get(f"{MCP_URL}/list_pending_approvals")
result = response.json()

pending = result.get("pending_approvals", [])
if pending:
    for item in pending:
        print(f"  - {item['filename']} (ID: {item['request_id']})")
else:
    print("  (No pending approvals)")
