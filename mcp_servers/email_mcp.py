"""
Email MCP Server
Provides email sending capabilities via Gmail SMTP
"""

import os
import sys
import smtplib
import base64
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from flask import Flask, request, jsonify
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import security modules
from security_config import get_security_config
from secure_action_executor import get_secure_executor


app = Flask(__name__)

VAULT_PATH = os.getenv("VAULT_PATH", r"D:\prompteng\AI_Employee_Vault")
SECURITY_CONFIG = get_security_config()
SECURE_EXECUTOR = get_secure_executor()

# Email configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_CONFIG = {
    "gmail_address": "",
    "app_password": ""  # Gmail App Password (not regular password)
}


def load_email_config():
    """Load email configuration from environment or config file"""
    global EMAIL_CONFIG
    
    # Try loading from .env file
    env_file = Path(__file__).parent.parent / '.env'
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Strip whitespace and quotes from value
                    value = value.strip().strip('"').strip("'")
                    if key == 'GMAIL_ADDRESS':
                        EMAIL_CONFIG['gmail_address'] = value
                    elif key == 'GMAIL_APP_PASSWORD':
                        EMAIL_CONFIG['gmail_password'] = value
    
    # Also check for credentials file
    creds_file = Path(__file__).parent.parent / 'gmail_credentials.json'
    if creds_file.exists():
        try:
            import json
            with open(creds_file, 'r') as f:
                creds = json.load(f)
                # Extract email from installed config if available
                if 'installed' in creds and 'client_email' in creds['installed']:
                    EMAIL_CONFIG['gmail_address'] = creds['installed']['client_email']
        except Exception:
            pass
    
    return EMAIL_CONFIG


def create_email_message(subject, body, to_email, from_email, html=False, attachments=None):
    """Create email message with optional attachments"""
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg['Date'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')
    
    # Add body
    mime_type = 'html' if html else 'plain'
    msg.attach(MIMEText(body, mime_type))
    
    # Add attachments
    if attachments:
        for attachment_path in attachments:
            try:
                with open(attachment_path, 'rb') as f:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(f.read())
                
                encoders.encode_base64(part)
                filename = os.path.basename(attachment_path)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename="{filename}"'
                )
                msg.attach(part)
            except Exception as e:
                SECURITY_CONFIG.logger.error(f"Error attaching file {attachment_path}: {e}")
    
    return msg


def send_email_smtp(to_email, subject, body, html=False, attachments=None):
    """Send email via Gmail SMTP"""
    config = load_email_config()
    
    from_email = config.get('gmail_address', '')
    password = config.get('gmail_password', '')
    
    if not from_email or not password:
        raise ValueError("Email credentials not configured. Set GMAIL_ADDRESS and GMAIL_APP_PASSWORD in .env")
    
    # Create message
    msg = create_email_message(subject, body, to_email, from_email, html, attachments)
    
    # Send via SMTP
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(from_email, password)
        server.send_message(msg)
        server.quit()
        
        return {
            "success": True,
            "message": f"Email sent to {to_email}",
            "to": to_email,
            "subject": subject
        }
    except smtplib.SMTPAuthenticationError:
        raise ValueError("SMTP authentication failed. Check Gmail App Password.")
    except smtplib.SMTPException as e:
        raise ValueError(f"SMTP error: {str(e)}")


@app.route('/capabilities', methods=['GET'])
def get_capabilities():
    """Return the capabilities of this MCP server"""
    config = load_email_config()
    capabilities = {
        "name": "email-mcp",
        "version": "1.0.0",
        "description": "Email sending operations for AI Employee",
        "operations": [
            {
                "name": "send_email",
                "description": "Send an email via Gmail SMTP",
                "parameters": {
                    "to": {"type": "string", "description": "Recipient email address"},
                    "subject": {"type": "string", "description": "Email subject"},
                    "body": {"type": "string", "description": "Email body content"},
                    "html": {"type": "boolean", "description": "Whether body is HTML (default: false)"},
                    "attachments": {"type": "array", "description": "List of file paths to attach"}
                }
            },
            {
                "name": "send_draft",
                "description": "Create a draft email (requires approval before sending)",
                "parameters": {
                    "to": {"type": "string", "description": "Recipient email address"},
                    "subject": {"type": "string", "description": "Email subject"},
                    "body": {"type": "string", "description": "Email body content"},
                    "html": {"type": "boolean", "description": "Whether body is HTML"}
                }
            }
        ],
        "configured": bool(config.get('gmail_address') and config.get('gmail_password'))
    }
    return jsonify(capabilities)


@app.route('/send_email', methods=['POST'])
def send_email():
    """Send an email"""
    data = request.json
    
    to_email = data.get('to', '')
    subject = data.get('subject', '')
    body = data.get('body', '')
    html = data.get('html', False)
    attachments = data.get('attachments', [])
    
    # Validate inputs
    if not to_email:
        return jsonify({"error": "Missing required parameter: to", "success": False}), 400
    if not subject:
        return jsonify({"error": "Missing required parameter: subject", "success": False}), 400
    if not body:
        return jsonify({"error": "Missing required parameter: body", "success": False}), 400
    
    # Validate attachments exist and are within vault
    valid_attachments = []
    for attachment_path in attachments:
        full_path = os.path.abspath(attachment_path)
        vault_path = os.path.abspath(VAULT_PATH)
        
        if not full_path.startswith(vault_path):
            SECURITY_CONFIG.logger.warning(f"Attachment attempt outside vault: {attachment_path}")
            return jsonify({
                "error": f"Attachment path outside vault: {attachment_path}",
                "success": False
            }), 403
        
        if not os.path.exists(attachment_path):
            return jsonify({
                "error": f"Attachment file not found: {attachment_path}",
                "success": False
            }), 404
        
        valid_attachments.append(full_path)
    
    try:
        # Sanitize inputs
        sanitized_to = SECURITY_CONFIG.sanitize_input(to_email)
        sanitized_subject = SECURITY_CONFIG.sanitize_input(subject)
        sanitized_body = SECURITY_CONFIG.sanitize_input(body)
        
        # Send email
        result = send_email_smtp(
            to_email=sanitized_to,
            subject=sanitized_subject,
            body=sanitized_body,
            html=html,
            attachments=valid_attachments if valid_attachments else None
        )
        
        # Log the email sending operation
        SECURITY_CONFIG.log_action(
            action_type="email_sent",
            actor="claude_code",
            target=to_email,
            parameters={
                "to": to_email,
                "subject": subject,
                "body_length": len(body),
                "attachment_count": len(valid_attachments)
            },
            approval_status="auto_approved",  # Could require approval for sensitive emails
            result="success"
        )
        
        return jsonify(result)
        
    except ValueError as e:
        SECURITY_CONFIG.logger.error(f"Email send failed: {str(e)}")
        return jsonify({"error": str(e), "success": False}), 400
    except Exception as e:
        SECURITY_CONFIG.logger.error(f"Unexpected error sending email: {str(e)}")
        return jsonify({"error": str(e), "success": False}), 500


@app.route('/send_draft', methods=['POST'])
def send_draft():
    """Create a draft email for approval before sending"""
    data = request.json
    
    to_email = data.get('to', '')
    subject = data.get('subject', '')
    body = data.get('body', '')
    html = data.get('html', False)
    
    # Validate inputs
    if not to_email or not subject or not body:
        return jsonify({
            "error": "Missing required parameters: to, subject, body",
            "success": False
        }), 400
    
    # Create draft file in Pending_Approval
    draft_dir = Path(VAULT_PATH) / "Pending_Approval" / "Email_Drafts"
    draft_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_subject = "".join(c if c.isalnum() else '_' for c in subject)[:30]
    filename = f"DRAFT_{safe_subject}_{timestamp}.md"
    filepath = draft_dir / filename
    
    content = f"""---
type: email_draft
to: {to_email}
subject: {subject}
created: {datetime.now().isoformat()}
status: pending_approval
---

# Email Draft

## To
{to_email}

## Subject
{subject}

## Body
{body}

---
## Approval Instructions
Move this file to `Approved/Email_Drafts/` to send, or `Rejected/Email_Drafts/` to discard.
"""
    
    filepath.write_text(content, encoding='utf-8')
    
    # Log the draft creation
    SECURITY_CONFIG.log_action(
        action_type="email_draft_created",
        actor="claude_code",
        target=to_email,
        parameters={"to": to_email, "subject": subject},
        approval_status="pending",
        result="success"
    )
    
    return jsonify({
        "success": True,
        "message": "Email draft created for approval",
        "filepath": str(filepath),
        "to": to_email,
        "subject": subject
    })


@app.route('/check_draft_status', methods=['POST'])
def check_draft_status():
    """Check if a draft email has been approved"""
    data = request.json
    filename = data.get('filename', '')
    
    draft_dir = Path(VAULT_PATH) / "Pending_Approval" / "Email_Drafts"
    approved_dir = Path(VAULT_PATH) / "Approved" / "Email_Drafts"
    rejected_dir = Path(VAULT_PATH) / "Rejected" / "Email_Drafts"
    
    pending_file = draft_dir / filename
    approved_file = approved_dir / filename
    rejected_file = rejected_dir / filename
    
    if approved_file.exists():
        return jsonify({"status": "approved", "location": str(approved_file)})
    elif rejected_file.exists():
        return jsonify({"status": "rejected", "location": str(rejected_file)})
    elif pending_file.exists():
        return jsonify({"status": "pending", "location": str(pending_file)})
    else:
        return jsonify({"status": "not_found", "message": "Draft not found"}), 404


@app.route('/execute_approved_draft', methods=['POST'])
def execute_approved_draft():
    """Send an approved draft email"""
    data = request.json
    filename = data.get('filename', '')
    
    approved_dir = Path(VAULT_PATH) / "Approved" / "Email_Drafts"
    approved_file = approved_dir / filename
    
    if not approved_file.exists():
        return jsonify({
            "error": "Draft not found in approved directory",
            "success": False
        }), 404
    
    try:
        # Parse the draft file
        content = approved_file.read_text(encoding='utf-8')
        
        # Extract email details from frontmatter
        to_email = subject = body = None
        lines = content.split('\n')
        in_frontmatter = False
        frontmatter_done = False
        
        for line in lines:
            if line.strip() == '---':
                if not in_frontmatter:
                    in_frontmatter = True
                else:
                    frontmatter_done = True
                continue
            
            if in_frontmatter:
                if line.startswith('to:'):
                    to_email = line.split(':', 1)[1].strip()
                elif line.startswith('subject:'):
                    subject = line.split(':', 1)[1].strip()
            elif frontmatter_done and line.startswith('## Body'):
                # Get body content (everything after ## Body header)
                body_start = lines.index(line) + 2  # Skip header and empty line
                body = '\n'.join(lines[body_start:]).strip()
                # Remove the approval instructions section
                if '---' in body:
                    body = body.split('---')[0].strip()
                break
        
        if not all([to_email, subject, body]):
            return jsonify({
                "error": "Could not parse email draft",
                "success": False
            }), 400
        
        # Send the email
        result = send_email_smtp(to_email, subject, body)
        
        # Move to Done folder
        done_dir = Path(VAULT_PATH) / "Done" / "Email_Drafts"
        done_dir.mkdir(parents=True, exist_ok=True)
        done_file = done_dir / filename
        approved_file.rename(done_file)
        
        # Log the operation
        SECURITY_CONFIG.log_action(
            action_type="email_sent_from_draft",
            actor="claude_code",
            target=to_email,
            parameters={"to": to_email, "subject": subject},
            approval_status="human_approved",
            result="success"
        )
        
        return jsonify({
            "success": True,
            "message": "Draft email sent successfully",
            "to": to_email,
            "subject": subject
        })
        
    except Exception as e:
        SECURITY_CONFIG.logger.error(f"Error sending approved draft: {e}")
        return jsonify({"error": str(e), "success": False}), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'email-mcp',
        'timestamp': datetime.now().isoformat()
    })


if __name__ == '__main__':
    # Load configuration on startup
    config = load_email_config()
    print(f"Email MCP Server starting...")
    print(f"Gmail configured: {bool(config.get('gmail_address'))}")
    
    # Ensure directories exist
    Path(VAULT_PATH).mkdir(parents=True, exist_ok=True)
    Path(VAULT_PATH, "Pending_Approval", "Email_Drafts").mkdir(parents=True, exist_ok=True)
    Path(VAULT_PATH, "Approved", "Email_Drafts").mkdir(parents=True, exist_ok=True)
    Path(VAULT_PATH, "Rejected", "Email_Drafts").mkdir(parents=True, exist_ok=True)
    Path(VAULT_PATH, "Done", "Email_Drafts").mkdir(parents=True, exist_ok=True)
    
    app.run(host='localhost', port=8001, debug=False)
