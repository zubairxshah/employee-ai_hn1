"""
WhatsApp Notification Service for AI Employee
Sends WhatsApp notifications when approval requests are created

Uses pywhatkit for simple WhatsApp Web automation
Alternative: Twilio API for production use
"""

import os
import sys
import time
import requests
from pathlib import Path
from datetime import datetime
import re
import pywhatkit

# Configuration
VAULT_PATH = r"D:\prompteng\AI_Employee_Vault"
PENDING_APPROVAL_DIR = os.path.join(VAULT_PATH, "Pending_Approval")
LOGS_DIR = os.path.join(VAULT_PATH, "Logs")

# Phone number to send notifications to (from .env or config)
# Format: +1234567890 (with country code, no spaces or special chars)
NOTIFICATION_PHONE = "+1234567890"  # TODO: Configure in .env

# Track notified files to avoid duplicates
NOTIFIED_FILES = set()


def load_phone_number():
    """Load notification phone number from .env file"""
    env_file = Path(__file__).parent / '.env'
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('WHATSAPP_NOTIFICATION_PHONE='):
                    return line.split('=', 1)[1].strip()
    return NOTIFICATION_PHONE


def parse_approval_file(filepath):
    """Parse approval request file to extract details"""
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
        
        return data
    except Exception as e:
        print(f"[ERROR] Failed to parse approval file {filepath}: {e}")
        return None


def send_whatsapp_notification(approval_data, filepath):
    """Send WhatsApp notification for new approval request"""
    try:
        filename = os.path.basename(filepath)
        
        # Extract approval details
        action_type = approval_data.get('action', 'unknown')
        amount = approval_data.get('amount', 'N/A')
        recipient = approval_data.get('recipient', 'N/A')
        reason = approval_data.get('reason', 'N/A')
        
        # Build notification message
        message = f"""🔔 *Approval Required*

*Action:* {action_type}
*Amount:* {amount}
*Recipient:* {recipient}
*Reason:* {reason}

Please review and approve in Obsidian vault:
{PENDING_APPROVAL_DIR}\\{filename}

_Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}"""
        
        print(f"[WHATSAPP] Sending notification...")
        print(f"  To: {NOTIFICATION_PHONE}")
        print(f"  Action: {action_type}")
        print(f"  Amount: {amount}")
        
        # Send via pywhatkit (WhatsApp Web automation)
        # This opens WhatsApp Web and sends the message
        # Note: Requires WhatsApp Web to be logged in
        
        # Calculate time (1 minute from now to allow WhatsApp Web to load)
        now = datetime.now()
        send_time_hour = now.hour
        send_time_minute = now.minute + 1
        
        # Handle minute overflow
        if send_time_minute >= 60:
            send_time_hour = (send_time_hour + 1) % 24
            send_time_minute = send_time_minute - 60
        
        # Send the message
        pywhatkit.sendwhatmsg(
            phone_no=NOTIFICATION_PHONE,
            message=message,
            time_hour=send_time_hour,
            time_min=send_time_minute,
            wait_time=15  # Wait 15 seconds for WhatsApp Web to load
        )
        
        print(f"[OK] WhatsApp notification sent!")
        return True, {"message": "Notification sent"}
        
    except Exception as e:
        print(f"[ERROR] Failed to send WhatsApp notification: {e}")
        return False, {"error": str(e)}


def send_whatsapp_notification_instant(approval_data, filepath):
    """Send WhatsApp notification instantly using pywhatkit's instant mode"""
    try:
        filename = os.path.basename(filepath)
        
        # Extract approval details
        action_type = approval_data.get('action', 'unknown')
        amount = approval_data.get('amount', 'N/A')
        recipient = approval_data.get('recipient', 'N/A')
        reason = approval_data.get('reason', 'N/A')
        
        # Build notification message (shorter for instant)
        message = f"""🔔 Approval Required

Action: {action_type}
Amount: {amount}
Recipient: {recipient}

Please review in Obsidian vault."""
        
        print(f"[WHATSAPP] Sending instant notification...")
        print(f"  To: {NOTIFICATION_PHONE}")
        
        # Use instant mode (opens in browser immediately)
        pywhatkit.sendwhatmsg_instantly(
            phone_no=NOTIFICATION_PHONE,
            message=message,
            wait_time=15,
            tab_close=True  # Close tab after sending
        )
        
        print(f"[OK] WhatsApp notification sent!")
        return True, {"message": "Instant notification sent"}
        
    except Exception as e:
        print(f"[ERROR] Failed to send WhatsApp notification: {e}")
        return False, {"error": str(e)}


def check_and_notify_new_approvals():
    """Check for new approval requests and send notifications"""
    notified_count = 0
    
    if os.path.exists(PENDING_APPROVAL_DIR):
        for filename in os.listdir(PENDING_APPROVAL_DIR):
            if filename.startswith("APPROVAL_") and filename.endswith(".md"):
                filepath = os.path.join(PENDING_APPROVAL_DIR, filename)
                
                # Skip if already notified
                if filepath in NOTIFIED_FILES:
                    continue
                
                print(f"\n{'='*60}")
                print(f"[NEW APPROVAL] Found: {filename}")
                print(f"{'='*60}")
                
                # Parse the approval file
                approval_data = parse_approval_file(filepath)
                if not approval_data:
                    print(f"[ERROR] Failed to parse approval file")
                    continue
                
                # Send WhatsApp notification
                success, result = send_whatsapp_notification_instant(approval_data, filepath)
                
                if success:
                    NOTIFIED_FILES.add(filepath)
                    notified_count += 1
                    
                    # Log the notification
                    log_notification(filename, "success", approval_data)
                else:
                    print(f"[ERROR] Notification failed: {result}")
                    log_notification(filename, "failed", approval_data, result.get('error', 'Unknown'))
    
    return notified_count


def log_notification(filename, status, approval_data, error=None):
    """Log notification to a log file"""
    Path(LOGS_DIR).mkdir(parents=True, exist_ok=True)
    log_file = os.path.join(LOGS_DIR, "whatsapp_notifications.log")
    
    timestamp = datetime.now().isoformat()
    action = approval_data.get('action', 'unknown')
    amount = approval_data.get('amount', 'N/A')
    
    log_entry = f"[{timestamp}] {filename}: {status} - {action} ({amount})"
    if error:
        log_entry += f" - Error: {error}"
    log_entry += "\n"
    
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(log_entry)


def run_notifier(poll_interval=10):
    """Run the WhatsApp notifier with polling"""
    print("=" * 60)
    print("WhatsApp Notification Service Starting...")
    print("=" * 60)
    print(f"Monitoring: {PENDING_APPROVAL_DIR}")
    print(f"Notification phone: {load_phone_number()}")
    print(f"Poll interval: {poll_interval} seconds")
    print(f"Press Ctrl+C to stop")
    print("=" * 60)
    
    try:
        while True:
            notified = check_and_notify_new_approvals()
            if notified > 0:
                print(f"\n[SUMMARY] Sent {notified} notification(s) this cycle")
            time.sleep(poll_interval)
    except KeyboardInterrupt:
        print("\n\nStopping WhatsApp Notification Service...")
    except Exception as e:
        print(f"\n[ERROR]Notifier crashed: {e}")
        raise


if __name__ == '__main__':
    # Run the notifier
    print("\nNote: WhatsApp Web must be logged in for this to work.")
    print("You will be prompted to scan QR code on first run.\n")
    run_notifier(poll_interval=10)
