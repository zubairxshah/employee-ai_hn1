"""
Send Test Email
Tests actual email sending with Gmail SMTP
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from skills.action import EmailMCPActionSkill

# Get the email skill
email_skill = EmailMCPActionSkill({'mcp_url': 'http://localhost:8001'})

print("=" * 60)
print("SENDING TEST EMAIL")
print("=" * 60)

# Send test email
result = email_skill.run(
    context={'vault_path': r'D:\prompteng\AI_Employee_Vault'},
    parameters={
        'action': 'send',
        'to': 'emaxis.newsletter@gmail.com',  # Send to self for testing
        'subject': '🤖 AI Employee Test Email',
        'body': '''Hello,

This is a test email from your AI Employee system.

If you received this, the Email MCP Server is working correctly!

Test Details:
- Server: Email MCP (port 8001)
- Skill: EmailMCPActionSkill
- Method: Gmail SMTP
- Timestamp: 2026-02-18

Best regards,
AI Employee System
---
Your Life and Business on Autopilot'''
    }
)

print("\nResult:")
if result.get('success'):
    print(f"[OK] Email sent successfully!")
    print(f"    To: {result.get('to')}")
    print(f"    Subject: {result.get('subject')}")
    print(f"    Message: {result.get('message')}")
else:
    print(f"[FAIL] Email send failed: {result.get('error')}")

print("\n" + "=" * 60)
