"""Simulate Claude creating an approval request via the Approval MCP server"""

import requests
import json

MCP_URL = "http://localhost:8003"

# Simulate Claude requesting approval for sending the $2,500 invoice
approval_data = {
    "action": "send_email",
    "amount": "$2,500.00",
    "recipient": "client.a@email.com",
    "reason": "February 2026 invoice #TEST-001 - 25 hours at $100/hour"
}

print("=" * 60)
print("STEP 1: Claude requests human approval")
print("=" * 60)
print(f"\nRequest data:")
print(json.dumps(approval_data, indent=2))

try:
    response = requests.post(f"{MCP_URL}/request_approval", json=approval_data)
    result = response.json()
    
    print(f"\nResponse:")
    print(json.dumps(result, indent=2))
    
    if result.get("success"):
        print(f"\n[OK] Approval request created!")
        print(f"     Request ID: {result.get('request_id')}")
        print(f"     File: {result.get('filepath')}")
        print(f"\n     The file is now in Pending_Approval folder.")
        print(f"     Waiting for human to review and approve...")
    else:
        print(f"\n[ERROR] Approval request failed: {result.get('message', 'Unknown error')}")
        
except requests.exceptions.RequestException as e:
    print(f"\n[ERROR] Failed to connect to Approval MCP server: {e}")
    print(f"          Make sure the server is running on port 8003")
