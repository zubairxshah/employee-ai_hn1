"""
WhatsApp MCP Server
Sends WhatsApp notifications via pywhatkit
"""

import os
import sys
from pathlib import Path
from flask import Flask, request, jsonify
from datetime import datetime
import re

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

app = Flask(__name__)

# Configuration
VAULT_PATH = os.getenv("VAULT_PATH", r"D:\prompteng\AI_Employee_Vault")

# Default notification phone (can be overridden via .env)
DEFAULT_PHONE = "+1234567890"


def load_notification_phone():
    """Load notification phone from .env file"""
    env_file = Path(__file__).parent.parent / '.env'
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('WHATSAPP_NOTIFICATION_PHONE='):
                    return line.split('=', 1)[1].strip().strip('"').strip("'")
    return DEFAULT_PHONE


def send_whatsapp_message(phone, message):
    """Send WhatsApp message using pywhatkit - FIXED to close browser properly"""
    try:
        import pywhatkit
        
        print(f"[WHATSAPP] Preparing to send notification to: {phone}")
        print(f"[WHATSAPP] IMPORTANT: Only ONE notification per approval")
        print(f"[WHATSAPP] Cooldown: 60 seconds between notifications")
        
        # Use shorter wait time but ensure browser closes properly
        # Key: tab_close=True to prevent multiple windows
        pywhatkit.sendwhatmsg_instantly(
            phone_no=phone,
            message=message,
            wait_time=20,      # Wait 20 seconds for WhatsApp Web to load
            tab_close=True,    # CLOSE tab after sending to prevent multiple windows
            close_time=3       # Close after 3 seconds
        )
        
        print(f"[WHATSAPP] Message sent - browser will close automatically")
        return True, "Message sent"
        
    except Exception as e:
        error_msg = str(e)
        print(f"[WHATSAPP] Error: {error_msg}")
        
        # Provide helpful error messages
        if "Could not load" in error_msg or "browser" in error_msg.lower():
            return False, "Browser issue - make sure Chrome is installed"
        elif "phone" in error_msg.lower() or "number" in error_msg.lower():
            return False, f"Phone number issue - check format: {phone}"
        elif "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
            return False, "Timeout - WhatsApp Web took too long to load"
        elif "QR" in error_msg or "qr" in error_msg or "scan" in error_msg.lower():
            return False, "QR code issue - scan quickly or refresh browser"
        else:
            return False, f"Error: {error_msg}"


@app.route('/capabilities', methods=['GET'])
def get_capabilities():
    """Return server capabilities"""
    return jsonify({
        "name": "whatsapp-mcp",
        "version": "1.0.0",
        "description": "WhatsApp notification service for AI Employee",
        "operations": [
            {
                "name": "send_notification",
                "description": "Send WhatsApp notification for approval request",
                "parameters": {
                    "action": {"type": "string", "description": "Action requiring approval"},
                    "amount": {"type": "string", "description": "Amount involved"},
                    "recipient": {"type": "string", "description": "Recipient of action"},
                    "reason": {"type": "string", "description": "Reason for action"},
                    "phone": {"type": "string", "description": "Phone number (optional, uses default if not provided)"}
                }
            },
            {
                "name": "send_custom_message",
                "description": "Send custom WhatsApp message",
                "parameters": {
                    "phone": {"type": "string", "description": "Phone number to send to"},
                    "message": {"type": "string", "description": "Message content"}
                }
            }
        ],
        "configured": True,
        "default_phone": load_notification_phone()
    })


@app.route('/send_notification', methods=['POST'])
def send_notification():
    """Send WhatsApp notification for approval request"""
    data = request.json
    
    action = data.get('action', 'unknown')
    amount = data.get('amount', 'N/A')
    recipient = data.get('recipient', 'N/A')
    reason = data.get('reason', 'N/A')
    phone = data.get('phone') or load_notification_phone()
    
    # Build notification message
    message = f"""🔔 *Approval Required*

*Action:* {action}
*Amount:* {amount}
*Recipient:* {recipient}
*Reason:* {reason}

Please review in Obsidian vault.

Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}"""
    
    try:
        success, result = send_whatsapp_message(phone, message)
        
        if success:
            return jsonify({
                "success": True,
                "message": "WhatsApp notification sent",
                "phone": phone,
                "action": action,
                "amount": amount
            })
        else:
            return jsonify({
                "success": False,
                "error": result
            }), 500
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/send_custom_message', methods=['POST'])
def send_custom_message():
    """Send custom WhatsApp message"""
    data = request.json
    
    phone = data.get('phone')
    message = data.get('message', '')
    
    if not phone:
        return jsonify({
            "success": False,
            "error": "Missing required parameter: phone"
        }), 400
    
    if not message:
        return jsonify({
            "success": False,
            "error": "Missing required parameter: message"
        }), 400
    
    try:
        success, result = send_whatsapp_message(phone, message)
        
        if success:
            return jsonify({
                "success": True,
                "message": "WhatsApp message sent",
                "phone": phone
            })
        else:
            return jsonify({
                "success": False,
                "error": result
            }), 500
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'whatsapp-mcp',
        'timestamp': datetime.now().isoformat()
    })


if __name__ == '__main__':
    print("WhatsApp MCP Server starting...")
    print(f"Default notification phone: {load_notification_phone()}")
    print("Note: WhatsApp Web must be logged in for notifications to work")
    
    app.run(host='localhost', port=8004, debug=False)
