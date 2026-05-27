"""Test sending a real email via Email MCP server"""

import requests

MCP_URL = "http://localhost:8001"

# Test email data
email_data = {
    "to": "emaxis.newsletter@gmail.com",  # Send to self for testing
    "subject": "AI Employee Test Email - Workflow Demo",
    "body": """Hello,

This is a test email from the AI Employee system.

This email was sent as part of the workflow integration demo:
1. File watcher detected task
2. Approval workflow created
3. Human approved the action
4. Email MCP server sent this email

Test completed successfully!

Best regards,
AI Employee System"""
}

print("=" * 60)
print("TEST: Send Real Email via Email MCP")
print("=" * 60)

print(f"\nEmail details:")
print(f"  To: {email_data['to']}")
print(f"  Subject: {email_data['subject']}")
print(f"  Body length: {len(email_data['body'])} chars")

try:
    response = requests.post(f"{MCP_URL}/send_email", json=email_data)
    result = response.json()
    
    print(f"\nResponse:")
    print(f"  Status code: {response.status_code}")
    print(f"  Result: {result}")
    
    if result.get("success"):
        print(f"\n[OK] Email sent successfully!")
        print(f"     Check inbox: {email_data['to']}")
    else:
        print(f"\n[ERROR] Email send failed: {result.get('error', 'Unknown error')}")
        
except requests.exceptions.RequestException as e:
    print(f"\n[ERROR] Failed to connect to Email MCP server: {e}")
    print(f"          Make sure the server is running on port 8001")
