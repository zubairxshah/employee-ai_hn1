"""
Complete Workflow Test: Approval → Email → Done
Tests the full integration of approval workflow with email sending
"""

import os
import sys
import time
import requests
import subprocess
import threading

VAULT_PATH = r"D:\prompteng\AI_Employee_Vault"
PENDING_DIR = os.path.join(VAULT_PATH, "Pending_Approval")
APPROVED_DIR = os.path.join(VAULT_PATH, "Approved")
DONE_DIR = os.path.join(VAULT_PATH, "Done")

APPROVAL_MCP_URL = "http://localhost:8003"
EMAIL_MCP_URL = "http://localhost:8001"


def check_servers():
    """Check if required MCP servers are running"""
    print("=" * 60)
    print("STEP 0: Checking MCP Servers")
    print("=" * 60)
    
    servers_ok = True
    
    # Check Approval MCP
    try:
        r = requests.get(f"{APPROVAL_MCP_URL}/list_pending_approvals", timeout=5)
        if r.status_code == 200:
            print(f"[OK] Approval MCP Server: Running on port 8003")
        else:
            print(f"[ERROR] Approval MCP Server: Unexpected response {r.status_code}")
            servers_ok = False
    except Exception as e:
        print(f"[ERROR] Approval MCP Server: Not running - {e}")
        servers_ok = False
    
    # Check Email MCP
    try:
        r = requests.get(f"{EMAIL_MCP_URL}/capabilities", timeout=5)
        if r.status_code == 200:
            configured = r.json().get('configured', False)
            status = "Configured" if configured else "Not Configured"
            print(f"[OK] Email MCP Server: Running on port 8001 ({status})")
            if not configured:
                print(f"[WARN] Email MCP not configured - check .env file")
        else:
            print(f"[ERROR] Email MCP Server: Unexpected response {r.status_code}")
            servers_ok = False
    except Exception as e:
        print(f"[ERROR] Email MCP Server: Not running - {e}")
        servers_ok = False
    
    return servers_ok


def create_approval_request():
    """Create a test approval request"""
    print("\n" + "=" * 60)
    print("STEP 1: Creating Approval Request")
    print("=" * 60)
    
    approval_data = {
        "action": "send_email",
        "amount": "$150.00",
        "recipient": "emaxis.newsletter@gmail.com",
        "reason": "Test invoice - Workflow integration demo"
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
            print(f"     File: {result.get('filepath')}")
            return result.get('request_id'), result.get('filepath')
        else:
            print(f"\n[ERROR] Failed to create approval: {result}")
            return None, None
            
    except Exception as e:
        print(f"\n[ERROR] Failed to create approval request: {e}")
        return None, None


def simulate_human_approval(request_id):
    """Simulate human approving by moving file to Approved"""
    print("\n" + "=" * 60)
    print("STEP 2: Simulating Human Approval")
    print("=" * 60)
    
    pending_file = os.path.join(PENDING_DIR, f"APPROVAL_{request_id}.md")
    approved_file = os.path.join(APPROVED_DIR, f"APPROVAL_{request_id}.md")
    
    # Wait a moment for file to be written
    time.sleep(1)
    
    if not os.path.exists(pending_file):
        print(f"[ERROR] Approval file not found: {pending_file}")
        return False
    
    # Ensure Approved directory exists
    os.makedirs(APPROVED_DIR, exist_ok=True)
    
    # Move file (simulating human action in Obsidian/Explorer)
    try:
        os.rename(pending_file, approved_file)
        print(f"[OK] File moved to Approved (human approval simulated)")
        print(f"     From: {pending_file}")
        print(f"     To:   {approved_file}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to move file: {e}")
        return False


def check_approval_status(request_id):
    """Check approval status via MCP"""
    print("\n" + "=" * 60)
    print("STEP 3: Checking Approval Status")
    print("=" * 60)
    
    try:
        response = requests.post(f"{APPROVAL_MCP_URL}/check_approval", json={"request_id": request_id}, timeout=10)
        result = response.json()
        
        status = result.get("status", "unknown")
        print(f"Status: {status.upper()}")
        
        return status
        
    except Exception as e:
        print(f"[ERROR] Failed to check status: {e}")
        return "error"


def wait_for_email_execution(request_id, timeout=30):
    """Wait for email to be sent and file moved to Done"""
    print("\n" + "=" * 60)
    print("STEP 4: Waiting for Email Execution")
    print("=" * 60)
    print(f"Timeout: {timeout} seconds")
    
    done_file = os.path.join(DONE_DIR, f"APPROVAL_{request_id}.md")
    approved_file = os.path.join(APPROVED_DIR, f"APPROVAL_{request_id}.md")
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        # Check if file moved to Done
        if os.path.exists(done_file):
            print(f"\n[OK] File moved to Done!")
            print(f"     Email was sent successfully!")
            return True
        
        # Check if still in Approved (waiting for executor)
        if os.path.exists(approved_file):
            print(f"[WAITING] File still in Approved - executor processing...")
        else:
            print(f"[WAITING] File not found in Approved or Done - checking...")
        
        time.sleep(2)
    
    print(f"\n[TIMEOUT] Waited {timeout} seconds - file not in Done")
    return False


def run_workflow_executor():
    """Start the workflow executor in a separate thread"""
    print("\n" + "=" * 60)
    print("Starting Approval Workflow Executor (background)")
    print("=" * 60)
    
    # Import and run executor
    from approval_workflow_executor import run_executor
    
    # Run in background thread
    executor_thread = threading.Thread(target=run_executor, args=(2,), daemon=True)
    executor_thread.start()
    
    print(f"[OK] Workflow executor started in background")
    return executor_thread


def main():
    """Run the complete workflow test"""
    print("\n" + "=" * 70)
    print("   COMPLETE WORKFLOW TEST: Approval -> Email -> Done")
    print("=" * 70)
    print(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # Step 0: Check servers
    if not check_servers():
        print("\n[ERROR] Required servers not running. Please start:")
        print("  python mcp_servers\\approval_mcp.py")
        print("  python mcp_servers\\email_mcp.py")
        return
    
    # Start workflow executor
    run_workflow_executor()
    
    # Give executor time to start
    time.sleep(2)
    
    # Step 1: Create approval request
    request_id, filepath = create_approval_request()
    if not request_id:
        print("\n[ERROR] Failed to create approval request")
        return
    
    # Step 2: Simulate human approval
    if not simulate_human_approval(request_id):
        print("\n[ERROR] Failed to simulate human approval")
        return
    
    # Step 3: Check approval status
    status = check_approval_status(request_id)
    if status != "approved":
        print(f"\n[ERROR] Approval status is not 'approved': {status}")
        return
    
    # Step 4: Wait for email execution
    if wait_for_email_execution(request_id, timeout=30):
        print("\n" + "=" * 70)
        print("   WORKFLOW TEST: SUCCESS!")
        print("=" * 70)
        print("""
Summary:
  - Approval request created
  - Human approval simulated (file moved to Approved)
  - Workflow executor detected approval
  - Email sent via Email MCP
  - File moved to Done

The complete approval -> email workflow is now integrated!
        """)
    else:
        print("\n" + "=" * 70)
        print("   WORKFLOW TEST: PARTIAL SUCCESS")
        print("=" * 70)
        print("""
Status:
  - Approval request created
  - Human approval simulated
  - Email execution timed out

Check:
  - Is approval_workflow_executor.py running?
  - Is email_mcp.py running?
  - Check Logs/approval_execution.log for errors
        """)


if __name__ == '__main__':
    main()
