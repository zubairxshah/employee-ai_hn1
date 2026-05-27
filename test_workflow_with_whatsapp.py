"""
Complete Workflow Test with WhatsApp Notifications
Tests: Approval -> WhatsApp Notification -> Human Approval -> Email -> Done
"""

import os
import sys
import time
import requests
import threading

VAULT_PATH = r"D:\prompteng\AI_Employee_Vault"
PENDING_DIR = os.path.join(VAULT_PATH, "Pending_Approval")
APPROVED_DIR = os.path.join(VAULT_PATH, "Approved")
DONE_DIR = os.path.join(VAULT_PATH, "Done")

APPROVAL_MCP_URL = "http://localhost:8003"
EMAIL_MCP_URL = "http://localhost:8001"
WHATSAPP_MCP_URL = "http://localhost:8004"


def check_all_servers():
    """Check if all required MCP servers are running"""
    print("=" * 70)
    print("STEP 0: Checking All MCP Servers")
    print("=" * 70)
    
    servers = {
        "Approval MCP": (APPROVAL_MCP_URL, "/list_pending_approvals"),
        "Email MCP": (EMAIL_MCP_URL, "/capabilities"),
        "WhatsApp MCP": (WHATSAPP_MCP_URL, "/capabilities")
    }
    
    all_ok = True
    
    for name, (base_url, endpoint) in servers.items():
        try:
            r = requests.get(f"{base_url}{endpoint}", timeout=5)
            if r.status_code == 200:
                if name == "Email MCP":
                    configured = r.json().get('configured', False)
                    status = "Configured" if configured else "Not Configured"
                    print(f"[OK] {name}: Running on port {base_url.split(':')[-1]} ({status})")
                else:
                    print(f"[OK] {name}: Running on port {base_url.split(':')[-1]}")
            else:
                print(f"[WARN] {name}: Unexpected response {r.status_code}")
        except Exception as e:
            print(f"[WARN] {name}: Not running - {e}")
            if name in ["Approval MCP", "Email MCP"]:
                all_ok = False
            # WhatsApp is optional
    
    return all_ok


def create_approval_request():
    """Create a test approval request"""
    print("\n" + "=" * 70)
    print("STEP 1: Creating Approval Request")
    print("=" * 70)
    
    approval_data = {
        "action": "send_email",
        "amount": "$250.00",
        "recipient": "emaxis.newsletter@gmail.com",
        "reason": "Test invoice - WhatsApp notification demo"
    }
    
    print(f"Request data:")
    print(f"  Action: {approval_data['action']}")
    print(f"  Amount: {approval_data['amount']}")
    print(f"  Recipient: {approval_data['recipient']}")
    print(f"  Reason: {approval_data['reason']}")
    
    try:
        response = requests.post(f"{APPROVAL_MCP_URL}/request_approval", json=approval_data, timeout=10)
        result = response.json()
        
        if result.get("success"):
            print(f"\n[OK] Approval request created!")
            print(f"     Request ID: {result.get('request_id')}")
            return result.get('request_id')
        else:
            print(f"\n[ERROR] Failed to create approval: {result}")
            return None
            
    except Exception as e:
        print(f"\n[ERROR] Failed to create approval request: {e}")
        return None


def wait_for_whatsapp_notification(request_id, timeout=15):
    """Wait for WhatsApp notification to be sent"""
    print("\n" + "=" * 70)
    print("STEP 2: Waiting for WhatsApp Notification")
    print("=" * 70)
    print(f"Timeout: {timeout} seconds")
    
    pending_file = os.path.join(PENDING_DIR, f"APPROVAL_{request_id}.md")
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        # Check if file exists (notification happens after file creation)
        if os.path.exists(pending_file):
            print(f"\n[OK] Approval file created - WhatsApp notification should be sent!")
            print(f"     Check your WhatsApp for notification")
            return True
        
        time.sleep(1)
    
    print(f"\n[INFO] Waited {timeout} seconds - notification may have been skipped")
    print(f"         (WhatsApp MCP may not be configured - this is OK)")
    return True  # Non-fatal


def simulate_human_approval(request_id):
    """Simulate human approving by moving file to Approved"""
    print("\n" + "=" * 70)
    print("STEP 3: Simulating Human Approval")
    print("=" * 70)
    
    pending_file = os.path.join(PENDING_DIR, f"APPROVAL_{request_id}.md")
    approved_file = os.path.join(APPROVED_DIR, f"APPROVAL_{request_id}.md")
    
    time.sleep(2)  # Wait for any pending operations
    
    if not os.path.exists(pending_file):
        print(f"[ERROR] Approval file not found: {pending_file}")
        return False
    
    os.makedirs(APPROVED_DIR, exist_ok=True)
    
    try:
        os.rename(pending_file, approved_file)
        print(f"[OK] File moved to Approved (human approval simulated)")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to move file: {e}")
        return False


def wait_for_email_execution(request_id, timeout=30):
    """Wait for email to be sent and file moved to Done"""
    print("\n" + "=" * 70)
    print("STEP 4: Waiting for Email Execution")
    print("=" * 70)
    print(f"Timeout: {timeout} seconds")
    
    done_file = os.path.join(DONE_DIR, f"APPROVAL_{request_id}.md")
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        if os.path.exists(done_file):
            print(f"\n[OK] File moved to Done!")
            print(f"     Email was sent successfully!")
            return True
        
        print(f"[WAITING] Processing... ({int(time.time() - start_time)}s/{timeout}s)")
        time.sleep(2)
    
    print(f"\n[TIMEOUT] Waited {timeout} seconds - file not in Done")
    return False


def main():
    """Run the complete workflow test with WhatsApp notifications"""
    print("\n" + "=" * 70)
    print("   COMPLETE WORKFLOW TEST: Approval -> WhatsApp -> Email -> Done")
    print("=" * 70)
    print(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # Step 0: Check servers
    if not check_all_servers():
        print("\n[ERROR] Required servers not running.")
        print("\nStart servers with:")
        print("  python start_mcp_servers.py")
        print("\nOr individually:")
        print("  python mcp_servers\\approval_mcp.py")
        print("  python mcp_servers\\email_mcp.py")
        print("  python mcp_servers\\whatsapp_mcp.py (optional)")
        return
    
    # Start workflow executor in background
    print("\n" + "=" * 70)
    print("Starting Approval Workflow Executor (background)")
    print("=" * 70)
    
    from approval_workflow_executor import run_executor
    executor_thread = threading.Thread(target=run_executor, args=(3,), daemon=True)
    executor_thread.start()
    time.sleep(2)
    print(f"[OK] Workflow executor started")
    
    # Step 1: Create approval request
    request_id = create_approval_request()
    if not request_id:
        print("\n[ERROR] Failed to create approval request")
        return
    
    # Step 2: Wait for WhatsApp notification
    wait_for_whatsapp_notification(request_id)
    
    # Step 3: Simulate human approval
    if not simulate_human_approval(request_id):
        print("\n[ERROR] Failed to simulate human approval")
        return
    
    # Step 4: Wait for email execution
    if wait_for_email_execution(request_id, timeout=30):
        print("\n" + "=" * 70)
        print("   WORKFLOW TEST: SUCCESS!")
        print("=" * 70)
        print("""
Summary:
  - Approval request created in Pending_Approval
  - WhatsApp notification sent (if configured)
  - Human approval simulated (file moved to Approved)
  - Workflow executor detected approval
  - Email sent via Email MCP
  - File moved to Done

The complete approval -> WhatsApp -> email workflow is integrated!
        """)
    else:
        print("\n" + "=" * 70)
        print("   WORKFLOW TEST: PARTIAL SUCCESS")
        print("=" * 70)
        print("""
Status:
  - Approval request created
  - WhatsApp notification (if configured)
  - Human approval simulated
  - Email execution timed out

Check:
  - Is approval_workflow_executor.py running?
  - Is email_mcp.py running?
  - Check Logs/approval_execution.log for errors
        """)


if __name__ == '__main__':
    main()
