"""Test Email Send - Direct"""
import sys
import time
sys.path.insert(0, '.')

from mcp_servers.email_mcp import send_email_gmail_api

print("=" * 60)
print("TESTING EMAIL SEND (Direct SMTP)")
print("=" * 60)

try:
    result = send_email_gmail_api(
        to_email='emaxis.newsletter@gmail.com',
        subject='🤖 AI Employee Test Email',
        body='''Hello,

This is a test email from your AI Employee system.

If you received this, the Email MCP Server is working correctly!

Test Details:
- Server: Email MCP (port 8001)
- Skill: EmailMCPActionSkill
- Method: Gmail SMTP
- Timestamp: 2026-02-18

Best regards,
AI Employee System'''
    )
    print("\n[SUCCESS] Email sent!")
    print(f"To: {result.get('to')}")
    print(f"Subject: {result.get('subject')}")
    print(f"Message: {result.get('message')}")
except Exception as e:
    print(f"\n[ERROR] {e}")

print("\n" + "=" * 60)
