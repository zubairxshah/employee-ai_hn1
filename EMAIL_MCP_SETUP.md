# Email MCP Server Setup Guide

## Overview
The Email MCP Server (port 8001) enables the AI Employee to send emails via Gmail SMTP.

## Prerequisites
- Gmail account with 2-Step Verification enabled
- Gmail App Password generated

## Step 1: Enable 2-Step Verification

1. Go to your Google Account: https://myaccount.google.com/
2. Click on **Security** in the left sidebar
3. Under "Signing in to Google", click **2-Step Verification**
4. Follow the setup process if not already enabled

## Step 2: Generate Gmail App Password

1. Go to: https://myaccount.google.com/apppasswords
2. Under "App passwords", select:
   - **App**: Mail
   - **Device**: Other (Custom name) → Enter "AI Employee"
3. Click **Generate**
4. Copy the 16-character password (format: `xxxx xxxx xxxx xxxx`)

**Important:** This is NOT your regular Gmail password. It's a special app password that allows SMTP access.

## Step 3: Configure .env File

Edit `D:\prompteng\employee\.env`:

```bash
# Gmail SMTP Credentials (for sending emails)
GMAIL_ADDRESS=emaxis.newsletter@gmail.com
GMAIL_APP_PASSWORD=abcd efgh ijkl mnop
```

**Note:** Enter the app password with or without spaces - both formats work.

## Step 4: Start the Email MCP Server

```bash
python mcp_servers/email_mcp.py
```

Expected output:
```
Email MCP Server starting...
Gmail configured: True
* Running on http://localhost:8001
```

## Step 5: Test Email Sending

### Option A: Test via Python Skill

```python
from skills.registry import get_skill

email_skill = get_skill('email_mcp_action')

# Send a test email
result = email_skill.run(
    context={'vault_path': r'D:\prompteng\AI_Employee_Vault'},
    parameters={
        'action': 'send',
        'to': 'recipient@example.com',
        'subject': 'Test Email',
        'body': 'This is a test email from AI Employee!'
    }
)

print(result)
```

### Option B: Test via API

```bash
curl -X POST http://localhost:8001/send_email \
  -H "Content-Type: application/json" \
  -d "{\"to\": \"recipient@example.com\", \"subject\": \"Test\", \"body\": \"Hello!\"}"
```

### Option C: Test via Capabilities

```bash
curl http://localhost:8001/capabilities
```

## Features

### Send Email
- Plain text or HTML body
- Optional attachments
- Automatic logging and audit trail

### Draft Email (Requires Approval)
- Creates draft in `Pending_Approval/Email_Drafts/`
- Human moves to `Approved/` to send
- Human moves to `Rejected/` to discard

### Check Draft Status
- Check if draft has been approved/rejected
- Get draft file location

### Execute Approved Draft
- Send email from approved draft
- Moves file to `Done/` after sending

## Security Features

| Feature | Description |
|---------|-------------|
| Vault Boundaries | Attachments must be within vault path |
| Input Sanitization | All inputs sanitized before use |
| Audit Logging | All email operations logged |
| Approval Workflow | Sensitive emails require human approval |
| Rate Limiting | Configurable max emails per hour |

## Troubleshooting

### "SMTP authentication failed"
- Verify App Password is correct (16 characters)
- Ensure 2-Step Verification is enabled
- Check GMAIL_ADDRESS matches your Gmail account

### "Connection refused" on port 8001
- Ensure Email MCP Server is running
- Check if port 8001 is already in use: `netstat -ano | findstr :8001`

### "Access denied: path outside vault"
- Attachment files must be within `D:\prompteng\AI_Employee_Vault`
- Use absolute paths for attachments

### "Email not sending"
- Check Gmail App Password hasn't expired
- Verify internet connection
- Check Gmail sending limits (500 emails/day for Gmail)

## Integration with Claude Code

Add to `.claude/config.json`:

```json
{
  "mcpServers": {
    "email-mcp": {
      "url": "http://localhost:8001",
      "enabled": true
    }
  }
}
```

## Email Templates

The AI can use templates stored in `Vault/Templates/Emails/`:

```markdown
# Invoice Email Template

To: {{recipient}}
Subject: Invoice {{invoice_number}}

Dear {{recipient_name}},

Please find attached invoice {{invoice_number}} for {{amount}}.

Payment is due within {{days}} days.

Best regards,
{{company_name}}
```

## Next Steps

After Email MCP is working:
1. Test with approval workflow
2. Create email templates
3. Integrate with Gmail Watcher for auto-replies
4. Move to Phase 3: LinkedIn MCP Server
