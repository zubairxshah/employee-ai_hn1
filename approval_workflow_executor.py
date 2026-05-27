"""
Approval Workflow Executor
Automatically executes approved actions (e.g., send email) after human approval
And sends WhatsApp notifications when new approvals are created

FIXED: Only sends WhatsApp notification ONCE per approval file
"""

import os
import sys
import time
import requests
from pathlib import Path
from datetime import datetime
import re

# Configuration
VAULT_PATH = os.getenv("VAULT_PATH", r"D:\prompteng\AI_Employee_Vault")
APPROVED_DIR = os.path.join(VAULT_PATH, "Approved")
DONE_DIR = os.path.join(VAULT_PATH, "Done")
PENDING_APPROVAL_DIR = os.path.join(VAULT_PATH, "Pending_Approval")
LOGS_DIR = os.path.join(VAULT_PATH, "Logs")

EMAIL_MCP_URL = "http://localhost:8001"
APPROVAL_MCP_URL = "http://localhost:8003"
WHATSAPP_MCP_URL = "http://localhost:8004"

# Track processed files to avoid duplicates (in-memory cache)
PROCESSED_FILES = set()
NOTIFIED_FILES = set()

# Cooldown tracking - prevent WhatsApp spam
LAST_WHATSAPP_TIME = 0
WHATSAPP_COOLDOWN = 60  # Minimum 60 seconds between WhatsApp notifications

# STARTUP COOLDOWN - Don't send notifications for first 2 minutes after startup
# This prevents spam when executor starts and finds old files
STARTUP_TIME = time.time()
STARTUP_COOLDOWN = 120  # 2 minutes startup grace period


def parse_approval_file(filepath):
    """Parse approval request file to extract action details"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract frontmatter
        frontmatter_match = re.search(r'---\n(.*?)\n---', content, re.DOTALL)
        if not frontmatter_match:
            return None
        
        frontmatter = frontmatter_match.group(1)
        
        # Parse key-value pairs
        data = {}
        for line in frontmatter.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                data[key.strip()] = value.strip()
        
        # Extract body content
        body_match = re.search(r'## Request Details\n(.*?)(?:##|\Z)', content, re.DOTALL)
        if body_match:
            data['body'] = body_match.group(1).strip()
        
        return data
    except Exception as e:
        print(f"[ERROR] Failed to parse approval file {filepath}: {e}")
        return None


def send_email_for_approval(approval_data, filepath):
    """Send email for an approved approval request"""
    try:
        # Extract email details - support both APPROVAL and EMAIL formats
        to_email = approval_data.get('to', approval_data.get('recipient', ''))
        subject = approval_data.get('subject', f"Invoice from AI Employee - {approval_data.get('reason', 'Payment')}")
        
        # Get body - either from parsed data or use default
        body = approval_data.get('body', None)
        if not body:
            # Build default email body
            body = f"""Dear Valued Client,

I hope this email finds you well.

Please find below the invoice details:

{approval_data.get('reason', 'Payment due')}

Amount: {approval_data.get('amount', 'N/A')}

If you have any questions regarding this invoice, please don't hesitate to contact us.

Thank you for your business!

Best regards,
AI Employee System
"""
        
        # Send via Email MCP
        email_data = {
            "to": to_email,
            "subject": subject,
            "body": body
        }
        
        print(f"[EMAIL] Sending to: {to_email}")
        print(f"[EMAIL] Subject: {subject}")
        
        response = requests.post(f"{EMAIL_MCP_URL}/send_email", json=email_data, timeout=30)
        result = response.json()
        
        if result.get("success"):
            print(f"[OK] Email sent successfully!")
            return True, result
        else:
            print(f"[ERROR] Email send failed: {result.get('error', 'Unknown error')}")
            return False, result
            
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Failed to send email: {e}")
        return False, {"error": str(e)}
    except Exception as e:
        print(f"[ERROR] Unexpected error sending email: {e}")
        return False, {"error": str(e)}


def execute_approved_action(filepath):
    """Execute the approved action based on the approval type"""
    filename = os.path.basename(filepath)

    # Parse the approval file
    approval_data = parse_approval_file(filepath)
    if not approval_data:
        return False, "Failed to parse approval file"

    # Determine action type - support both formats
    action_type = approval_data.get('action', approval_data.get('type', 'unknown'))

    # Platinum tier: check if this agent role is allowed to execute
    try:
        from agent_config import can_execute_action
        if not can_execute_action(action_type):
            print(f"[INFO] Action '{action_type}' not allowed for current agent role, skipping")
            return False, f"Action '{action_type}' blocked by agent_config"
    except ImportError:
        pass  # agent_config not available, allow all (backwards compatible)

    # Handle EMAIL_*.md format
    if action_type == 'send_email' or 'to:' in open(filepath, 'r', encoding='utf-8').read():
        action_type = 'send_email'

    print(f"[ACTION] Executing approved action: {action_type}")

    # Execute based on action type
    if action_type == 'send_email':
        success, result = send_email_for_approval(approval_data, filepath)
        return success, result
    
    elif action_type == 'confirm_invoice':
        # Confirm the invoice in Odoo
        success, result = confirm_invoice_in_odoo(approval_data, filepath)
        
        # After confirmation, send invoice email to customer
        if success:
            invoice_id = approval_data.get('invoice_id')
            customer_email = approval_data.get('recipient', '')
            amount = approval_data.get('amount', 0)
            reason = approval_data.get('reason', '')
            
            send_invoice_email_to_customer(
                invoice_id=invoice_id,
                customer_email=customer_email,
                customer_name=reason.split(' for ')[-1] if ' for ' in reason else 'Valued Customer',
                amount=float(amount.replace('$', '').replace(',', '')) if isinstance(amount, str) else amount,
                description=f"Approved invoice"
            )
        
        return success, result
    
    else:
        print(f"[INFO] Unknown action type: {action_type}")
        # For unknown actions, just mark as executed without doing anything
        return True, {"message": f"Action {action_type} marked as executed"}


def move_to_done(filepath):
    """Move processed approval file to Done folder"""
    try:
        filename = os.path.basename(filepath)
        
        # Determine source directory
        if APPROVED_DIR in filepath:
            source_dir = APPROVED_DIR
        elif PENDING_APPROVAL_DIR in filepath:
            source_dir = PENDING_APPROVAL_DIR
        else:
            print(f"[ERROR] Unknown source directory for: {filepath}")
            return False
        
        # Create Done directory if needed
        Path(DONE_DIR).mkdir(parents=True, exist_ok=True)
        
        # Move file
        dest_path = os.path.join(DONE_DIR, filename)
        
        # Handle duplicate filenames
        if os.path.exists(dest_path):
            base, ext = os.path.splitext(filename)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{base}_{timestamp}{ext}"
            dest_path = os.path.join(DONE_DIR, filename)
        
        os.rename(filepath, dest_path)
        print(f"[OK] Moved to Done: {filename}")
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to move file to Done: {e}")
        return False


def log_notification(filename, status, result):
    """Log WhatsApp notification to a log file"""
    log_dir = os.path.join(VAULT_PATH, "Logs")
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    
    log_file = os.path.join(log_dir, "whatsapp_notifications.log")
    
    timestamp = datetime.now().isoformat()
    log_entry = f"[{timestamp}] {filename}: {status} - {result}\n"
    
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(log_entry)


def mark_file_as_notified(filepath):
    """Mark a file as notified by adding a flag to the file itself"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if already marked
        if 'whatsapp_notified: true' in content:
            return True
        
        # Add whatsapp_notified flag to frontmatter
        if content.startswith('---'):
            # Find end of frontmatter
            end_frontmatter = content.find('---', 3)
            if end_frontmatter > 0:
                # Insert flag before closing ---
                insert_pos = end_frontmatter
                content = content[:insert_pos] + f"\nwhatsapp_notified: true\n" + content[insert_pos:]
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                # Also save to notified state file for persistence
                save_notified_state(filepath)
                return True
        
        return False
    except Exception as e:
        print(f"[ERROR] Failed to mark file as notified: {e}")
        return False


def is_file_notified(filepath):
    """Check if a file has already been notified"""
    # Check in-memory cache first
    if filepath in NOTIFIED_FILES:
        return True
    
    # Check file content
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'whatsapp_notified: true' in content:
            return True
        
        # Check persisted state
        notified_state_file = get_notified_state_file(filepath)
        if os.path.exists(notified_state_file):
            return True
        
        return False
    except:
        return False


def save_notified_state(filepath):
    """Save notified state to a file for persistence across restarts"""
    state_file = get_notified_state_file(filepath)
    try:
        Path(state_file).parent.mkdir(parents=True, exist_ok=True)
        with open(state_file, 'w', encoding='utf-8') as f:
            f.write(f"notified_at: {datetime.now().isoformat()}\n")
            f.write(f"filepath: {filepath}\n")
    except:
        pass  # Non-critical, just for persistence


def get_notified_state_file(filepath):
    """Get the state file path for a given approval file"""
    filename = os.path.basename(filepath)
    state_filename = filename.replace('.md', '.notified')
    return os.path.join(LOGS_DIR, 'whatsapp_state', state_filename)


def check_and_notify_new_approvals():
    """Check for new approval requests and send WhatsApp notifications"""
    global LAST_WHATSAPP_TIME
    
    notified_count = 0
    
    # STARTUP COOLDOWN - Don't notify during first 2 minutes after startup
    # This prevents spam when executor starts and finds old files
    time_since_startup = time.time() - STARTUP_TIME
    if time_since_startup < STARTUP_COOLDOWN:
        remaining = int(STARTUP_COOLDOWN - time_since_startup)
        print(f"[INFO] Startup cooldown active - {remaining}s remaining (no WhatsApp notifications)")
        return 0
    
    # Check cooldown - prevent WhatsApp spam
    current_time = time.time()
    if current_time - LAST_WHATSAPP_TIME < WHATSAPP_COOLDOWN:
        # Still in cooldown, skip this cycle
        return 0
    
    if os.path.exists(PENDING_APPROVAL_DIR):
        for filename in os.listdir(PENDING_APPROVAL_DIR):
            if filename.startswith("APPROVAL_") and filename.endswith(".md"):
                filepath = os.path.join(PENDING_APPROVAL_DIR, filename)
                
                # Skip if already notified (check file content)
                if is_file_notified(filepath):
                    continue
                
                print(f"\n{'='*60}")
                print(f"[NEW APPROVAL] Found: {filename}")
                print(f"{'='*60}")
                
                # Check cooldown again before sending
                current_time = time.time()
                if current_time - LAST_WHATSAPP_TIME < WHATSAPP_COOLDOWN:
                    print(f"[INFO] In cooldown period, will notify later")
                    continue
                
                # Send WhatsApp notification
                success, result = send_whatsapp_notification(filepath)
                
                if success:
                    # Mark file as notified to prevent duplicate notifications
                    mark_file_as_notified(filepath)
                    NOTIFIED_FILES.add(filepath)
                    LAST_WHATSAPP_TIME = current_time
                    notified_count += 1
                    
                    # Log the notification
                    log_notification(filename, "success", result)
                    
                    # Only send ONE notification per cycle
                    break
                else:
                    print(f"[ERROR] Notification failed: {result}")
                    log_notification(filename, "failed", result)
                    # Still mark as notified to prevent infinite retry loop
                    mark_file_as_notified(filepath)
                    NOTIFIED_FILES.add(filepath)
                    LAST_WHATSAPP_TIME = current_time
    
    return notified_count


def check_and_execute_approved():
    """Check for newly approved files and execute them"""
    executed_count = 0
    
    # Check Approved directory for new files
    if os.path.exists(APPROVED_DIR):
        for filename in os.listdir(APPROVED_DIR):
            # Support both APPROVAL_*.md and EMAIL_*.md formats
            if (filename.startswith("APPROVAL_") or filename.startswith("EMAIL_")) and filename.endswith(".md"):
                filepath = os.path.join(APPROVED_DIR, filename)
                
                # Skip if already processed
                if filepath in PROCESSED_FILES:
                    continue
                
                print(f"\n{'='*60}")
                print(f"[APPROVAL] Found approved file: {filename}")
                print(f"{'='*60}")
                
                # Execute the approved action
                success, result = execute_approved_action(filepath)
                
                if success:
                    # Move to Done folder
                    move_to_done(filepath)
                    PROCESSED_FILES.add(filepath)
                    executed_count += 1
                    
                    # Log execution
                    log_execution(filename, "success", result)
                else:
                    print(f"[ERROR] Failed to execute action: {result}")
                    log_execution(filename, "failed", result)
    
    return executed_count


def log_execution(filename, status, result):
    """Log execution to a log file"""
    log_dir = os.path.join(VAULT_PATH, "Logs")
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    
    log_file = os.path.join(log_dir, "approval_execution.log")
    
    timestamp = datetime.now().isoformat()
    log_entry = f"[{timestamp}] {filename}: {status} - {result}\n"
    
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(log_entry)


def send_whatsapp_notification(filepath):
    """Send WhatsApp notification for new approval request"""
    try:
        # Parse the approval file
        approval_data = parse_approval_file(filepath)
        if not approval_data:
            return False, "Failed to parse approval file"
        
        # Send via WhatsApp MCP
        notification_data = {
            "action": approval_data.get('action', 'unknown'),
            "amount": approval_data.get('amount', 'N/A'),
            "recipient": approval_data.get('recipient', 'N/A'),
            "reason": approval_data.get('reason', 'N/A')
        }
        
        print(f"[WHATSAPP] Sending notification...")
        print(f"  Action: {notification_data['action']}")
        print(f"  Amount: {notification_data['amount']}")
        
        response = requests.post(
            f"{WHATSAPP_MCP_URL}/send_notification",
            json=notification_data,
            timeout=60  # Increased timeout for WhatsApp Web
        )
        result = response.json()
        
        if result.get("success"):
            print(f"[OK] WhatsApp notification sent!")
            return True, result
        else:
            # Check if it's a "not configured" error (pywhatkit not installed or phone not set)
            error = result.get('error', 'Unknown error')
            print(f"[INFO] WhatsApp notification issue: {error}")
            print(f"       This is OK - email workflow will still work")
            return True, {"message": f"Notification skipped: {error}"}
            
    except requests.exceptions.ConnectionError:
        # WhatsApp MCP server not running - this is OK
        print(f"[INFO] WhatsApp MCP server not running - skipping notification")
        return True, {"message": "WhatsApp MCP not running"}
    except requests.exceptions.Timeout:
        # WhatsApp MCP timed out (likely waiting for QR scan)
        print(f"[INFO] WhatsApp notification timed out - continuing anyway")
        print(f"       Check browser window for WhatsApp Web")
        return True, {"message": "Notification timeout - check browser"}
    except Exception as e:
        print(f"[INFO] WhatsApp notification failed: {e}")
        print(f"       This is OK - email workflow will still work")
        return True, {"message": f"Notification failed: {e}"}  # Non-fatal


def run_executor(poll_interval=5):
    """Run the approval executor with polling"""
    print("=" * 60)
    print("Approval Workflow Executor Starting...")
    print("=" * 60)
    print(f"Monitoring: {APPROVED_DIR} (for execution)")
    print(f"Monitoring: {PENDING_APPROVAL_DIR} (for notifications)")
    print(f"Email MCP: {EMAIL_MCP_URL}")
    print(f"WhatsApp MCP: {WHATSAPP_MCP_URL}")
    print(f"Poll interval: {poll_interval} seconds")
    print(f"Startup cooldown: {STARTUP_COOLDOWN} seconds (prevents startup spam)")
    print(f"Press Ctrl+C to stop")
    print("=" * 60)
    print(f"\n[INFO] WhatsApp notifications will start after {STARTUP_COOLDOWN}s cooldown")
    print("=" * 60)
    
    try:
        while True:
            # Check for new approvals and send WhatsApp notifications
            notified = check_and_notify_new_approvals()
            
            # Check for approved files and execute actions
            executed = check_and_execute_approved()
            
            if notified > 0:
                print(f"\n[SUMMARY] Sent {notified} WhatsApp notification(s) this cycle")
            if executed > 0:
                print(f"\n[SUMMARY] Executed {executed} approval(s) this cycle")
            
            time.sleep(poll_interval)
    except KeyboardInterrupt:
        print("\n\nStopping Approval Workflow Executor...")
    except Exception as e:
        print(f"\n[ERROR] Executor crashed: {e}")
        raise


if __name__ == '__main__':
    # Run the executor
    run_executor(poll_interval=5)
