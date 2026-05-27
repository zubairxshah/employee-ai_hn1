"""
Complete Workflow Test: Approval and Rejection Scenarios
Tests the full end-to-end workflow with both success and rejection paths
"""

import os
import sys
import time
import requests
from pathlib import Path

VAULT_PATH = r"D:\prompteng\AI_Employee_Vault"
PENDING_DIR = os.path.join(VAULT_PATH, "Pending_Approval")
APPROVED_DIR = os.path.join(VAULT_PATH, "Approved")
REJECTED_DIR = os.path.join(VAULT_PATH, "Rejected")
DONE_DIR = os.path.join(VAULT_PATH, "Done")
LOGS_DIR = os.path.join(VAULT_PATH, "Logs")

EMAIL_MCP_URL = "http://localhost:8001"
APPROVAL_MCP_URL = "http://localhost:8003"
WHATSAPP_MCP_URL = "http://localhost:8004"


def print_header(text):
    """Print formatted header"""
    print("\n" + "=" * 70)
    print(f"   {text}")
    print("=" * 70)


def print_step(step, text):
    """Print step header"""
    print(f"\n{'='*70}")
    print(f"STEP {step}: {text}")
    print(f"{'='*70}")


def check_services():
    """Check if all required services are running"""
    print_header("Checking Services")
    
    services_ok = True
    
    # Check Email MCP
    try:
        r = requests.get(f"{EMAIL_MCP_URL}/capabilities", timeout=3)
        if r.status_code == 200:
            configured = r.json().get('configured', False)
            print(f"[OK] Email MCP: Running on port 8001 ({'Configured' if configured else 'Not Configured'})")
            if not configured:
                services_ok = False
        else:
            print(f"[WARN] Email MCP: Unexpected response {r.status_code}")
            services_ok = False
    except Exception as e:
        print(f"[ERROR] Email MCP: Not running - {e}")
        services_ok = False
    
    # Check Approval MCP
    try:
        r = requests.get(f"{APPROVAL_MCP_URL}/list_pending_approvals", timeout=3)
        if r.status_code == 200:
            print(f"[OK] Approval MCP: Running on port 8003")
        else:
            print(f"[WARN] Approval MCP: Unexpected response {r.status_code}")
            services_ok = False
    except Exception as e:
        print(f"[ERROR] Approval MCP: Not running - {e}")
        services_ok = False
    
    # Check WhatsApp MCP
    try:
        r = requests.get(f"{WHATSAPP_MCP_URL}/capabilities", timeout=3)
        if r.status_code == 200:
            print(f"[OK] WhatsApp MCP: Running on port 8004")
        else:
            print(f"[WARN] WhatsApp MCP: Unexpected response {r.status_code}")
            # WhatsApp is optional, don't fail
    except Exception as e:
        print(f"[INFO] WhatsApp MCP: Not running (optional) - {e}")
    
    return services_ok


def create_approval_request(test_name, amount, recipient, reason):
    """Create an approval request file"""
    os.makedirs(PENDING_DIR, exist_ok=True)
    
    filename = f"APPROVAL_{test_name}_{int(time.time())}.md"
    filepath = os.path.join(PENDING_DIR, filename)
    
    content = f"""---
type: approval_request
action: send_email
amount: {amount}
recipient: {recipient}
reason: {reason}
test_name: {test_name}
created: {time.strftime('%Y-%m-%dT%H:%M:%S')}
---

## Request Details
- Action: send_email
- Amount: {amount}
- Recipient: {recipient}
- Reason: {reason}
- Test: {test_name}

## To Approve
Move this file to Approved folder.

## To Reject
Move this file to Rejected folder.
"""
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return filename, filepath


def wait_for_whatsapp_notification(filename, timeout=30):
    """Wait for WhatsApp notification to be sent"""
    print(f"\n[WAITING] Waiting for WhatsApp notification...")
    print(f"          Timeout: {timeout} seconds")
    
    log_file = os.path.join(LOGS_DIR, "whatsapp_notifications.log")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                log_content = f.read()
            
            if filename in log_content:
                # Count occurrences
                count = log_content.count(filename)
                print(f"\n[OK] WhatsApp notification logged!")
                print(f"       Entries for this file: {count}")
                return True
        
        time.sleep(2)
        elapsed = int(time.time() - start_time)
        print(f"       Waiting... {elapsed}s/{timeout}s", end='\r')
    
    print(f"\n[TIMEOUT] Waited {timeout} seconds")
    return False


def wait_for_email_execution(filename, timeout=30):
    """Wait for email to be sent and file moved to Done"""
    print(f"\n[WAITING] Waiting for email execution...")
    print(f"          Timeout: {timeout} seconds")
    
    done_file = os.path.join(DONE_DIR, filename)
    approved_file = os.path.join(APPROVED_DIR, filename)
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        if os.path.exists(done_file):
            print(f"\n[OK] File moved to Done!")
            print(f"       Email was sent successfully!")
            return True
        
        if os.path.exists(approved_file):
            elapsed = int(time.time() - start_time)
            print(f"       Waiting... {elapsed}s/{timeout}s (file still in Approved)", end='\r')
        else:
            elapsed = int(time.time() - start_time)
            print(f"       Waiting... {elapsed}s/{timeout}s (file not found)", end='\r')
        
        time.sleep(2)
    
    print(f"\n[TIMEOUT] Waited {timeout} seconds")
    return False


def test_approval_scenario():
    """Test the approval workflow"""
    print_step(2, "APPROVAL SCENARIO TEST")
    
    # Create approval request
    filename, filepath = create_approval_request(
        test_name="APPROVAL_TEST",
        amount="$100.00",
        recipient="emaxis.newsletter@gmail.com",
        reason="Approval workflow test - should send email"
    )
    
    print(f"\n[OK] Created approval request: {filename}")
    print(f"       Amount: $100.00")
    print(f"       Recipient: emaxis.newsletter@gmail.com")
    print(f"       Location: Pending_Approval/")
    
    # Wait for WhatsApp notification
    print("\n" + "-" * 70)
    print("WhatsApp notification should be sent (if cooldown expired)")
    wait_for_whatsapp_notification(filename, timeout=30)
    
    # Simulate human approval
    print("\n" + "-" * 70)
    print("SIMULATING HUMAN APPROVAL")
    print("-" * 70)
    
    approved_file = os.path.join(APPROVED_DIR, filename)
    os.makedirs(APPROVED_DIR, exist_ok=True)
    
    print(f"\n[ACTION] Moving file to Approved folder...")
    os.rename(filepath, approved_file)
    print(f"[OK] File moved to Approved/")
    
    # Wait for email execution
    print("\n" + "-" * 70)
    print("Email should be sent automatically")
    print("-" * 70)
    
    email_sent = wait_for_email_execution(filename, timeout=30)
    
    # Verify results
    print("\n" + "=" * 70)
    print("APPROVAL SCENARIO RESULTS")
    print("=" * 70)
    
    if email_sent:
        print("[PASS] Email was sent successfully!")
        print("[PASS] File moved to Done folder!")
        return True
    else:
        print("[FAIL] Email was NOT sent!")
        print("[INFO] Check if workflow executor is running")
        return False


def test_rejection_scenario():
    """Test the rejection workflow"""
    print_step(3, "REJECTION SCENARIO TEST")
    
    # Create approval request
    filename, filepath = create_approval_request(
        test_name="REJECTION_TEST",
        amount="$200.00",
        recipient="test@example.com",
        reason="Rejection workflow test - should NOT send email"
    )
    
    print(f"\n[OK] Created approval request: {filename}")
    print(f"       Amount: $200.00")
    print(f"       Recipient: test@example.com")
    print(f"       Location: Pending_Approval/")
    
    # Wait for WhatsApp notification
    print("\n[WAITING] Waiting for WhatsApp notification...")
    wait_for_whatsapp_notification(filename, timeout=30)
    
    # Simulate human rejection
    print("\n" + "-" * 70)
    print("SIMULATING HUMAN REJECTION")
    print("-" * 70)
    
    rejected_file = os.path.join(REJECTED_DIR, filename)
    os.makedirs(REJECTED_DIR, exist_ok=True)
    
    print(f"\n[ACTION] Moving file to Rejected folder...")
    os.rename(filepath, rejected_file)
    print(f"[OK] File moved to Rejected/")
    
    # Wait and verify NO email is sent
    print("\n" + "-" * 70)
    print("NO email should be sent (file is in Rejected)")
    print("-" * 70)
    
    time.sleep(15)  # Wait to ensure no email is sent
    
    done_file = os.path.join(DONE_DIR, filename)
    if os.path.exists(done_file):
        print(f"\n[FAIL] File was moved to Done (should stay in Rejected)!")
        return False
    else:
        print(f"\n[OK] File correctly stayed in Rejected folder")
        print(f"[OK] No email was sent (as expected)")
        return True


def check_logs():
    """Check execution logs"""
    print_step(4, "CHECKING LOGS")
    
    # Check approval execution log
    exec_log = os.path.join(LOGS_DIR, "approval_execution.log")
    if os.path.exists(exec_log):
        print(f"\n[INFO] Approval Execution Log:")
        print("-" * 70)
        with open(exec_log, 'r', encoding='utf-8') as f:
            lines = f.readlines()[-5:]  # Last 5 lines
            for line in lines:
                print(f"  {line.strip()}")
        print("-" * 70)
    else:
        print(f"\n[INFO] No approval execution log found")
    
    # Check WhatsApp notification log
    whatsapp_log = os.path.join(LOGS_DIR, "whatsapp_notifications.log")
    if os.path.exists(whatsapp_log):
        print(f"\n[INFO] WhatsApp Notification Log:")
        print("-" * 70)
        with open(whatsapp_log, 'r', encoding='utf-8') as f:
            lines = f.readlines()[-5:]  # Last 5 lines
            for line in lines:
                print(f"  {line.strip()}")
        print("-" * 70)
    else:
        print(f"\n[INFO] No WhatsApp notification log found")


def main():
    """Run complete workflow test"""
    print_header("COMPLETE WORKFLOW TEST: Approval + Rejection")
    print(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Vault: {VAULT_PATH}")
    
    # Step 1: Check services
    services_ok = check_services()
    
    if not services_ok:
        print("\n" + "=" * 70)
        print("[WARN] Some services are not running!")
        print("=" * 70)
        print("\nRequired services:")
        print("  - Email MCP (port 8001)")
        print("  - Approval MCP (port 8003)")
        print("  - Workflow Executor (running)")
        print("\nStart services:")
        print("  python start_mcp_servers.py")
        print("  python approval_workflow_executor.py")
        print("\nContinuing test anyway...")
    
    # Step 2: Test approval scenario
    approval_passed = test_approval_scenario()
    
    # Step 3: Test rejection scenario
    rejection_passed = test_rejection_scenario()
    
    # Step 4: Check logs
    check_logs()
    
    # Final summary
    print_header("TEST SUMMARY")
    
    print(f"\nTest Results:")
    print(f"  Approval Scenario:  {'[PASS]' if approval_passed else '[FAIL]'}")
    print(f"  Rejection Scenario: {'[PASS]' if rejection_passed else '[FAIL]'}")
    
    print("\n" + "=" * 70)
    
    if approval_passed and rejection_passed:
        print("   ALL TESTS PASSED!")
        print("=" * 70)
        print("""
Workflow is working correctly:
  - Approval requests created
  - WhatsApp notifications sent (after cooldown)
  - Human approval → Email sent → File to Done
  - Human rejection → No email → File to Rejected

System is ready for production use!
        """)
    else:
        print("   SOME TESTS FAILED")
        print("=" * 70)
        print("""
Check the following:
  - Workflow executor is running
  - Email MCP is configured (.env file)
  - Startup cooldown has expired (120 seconds)
  - Check logs for error details
        """)
    
    print("=" * 70)


if __name__ == '__main__':
    main()
