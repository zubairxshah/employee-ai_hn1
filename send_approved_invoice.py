"""
Send the approved invoice email from EMAIL_invoice_client_a.md
"""

import requests

EMAIL_MCP_URL = "http://localhost:8001"

# Email details from the approved file
email_data = {
    "to": "client.a@email.com",
    "subject": "January 2026 Invoice - $1,500",
    "body": """Dear Valued Client,

I hope this email finds you well.

Please find attached your invoice for January 2026.

Invoice Details:
- Period: January 2026
- Amount: $1,500.00
- Due Date: As per agreement

If you have any questions regarding this invoice, please don't hesitate to contact us.

Thank you for your business!

Best regards,
AI Employee System
"""
}

print("=" * 60)
print("Sending Approved Invoice Email")
print("=" * 60)
print(f"To: {email_data['to']}")
print(f"Subject: {email_data['subject']}")

try:
    response = requests.post(f"{EMAIL_MCP_URL}/send_email", json=email_data, timeout=30)
    result = response.json()
    
    if result.get("success"):
        print(f"\n[OK] Email sent successfully!")
        print(f"     Message: {result.get('message')}")
    else:
        print(f"\n[ERROR] Email send failed: {result.get('error')}")
        
except Exception as e:
    print(f"\n[ERROR] Failed to send email: {e}")
