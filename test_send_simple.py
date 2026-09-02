"""Test Email Send - No Emoji"""
import sys
sys.path.insert(0, '.')

from mcp_servers.email_mcp import send_email_gmail_api

print("Testing email send...")

try:
    result = send_email_gmail_api(
        to_email='emaxis.newsletter@gmail.com',
        subject='AI Employee Test Email',
        body='''Hello,

This is a test email from your AI Employee system.

If you received this, the Email MCP Server is working correctly!

Best regards,
AI Employee System'''
    )
    print("[SUCCESS] Email sent!")
    print(f"To: {result.get('to')}")
    print(f"Subject: {result.get('subject')}")
    print(f"Message: {result.get('message')}")
except Exception as e:
    print(f"[ERROR] {e}")
