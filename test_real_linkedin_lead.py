"""
Real LinkedIn Lead Test - Interactive
Copy-paste real LinkedIn message data and test the workflow
"""

import json
from linkedin_to_customer_workflow import process_linkedin_message

print("=" * 70)
print("  REAL LINKEDIN LEAD TEST")
print("=" * 70)
print("\nInstructions:")
print("1. Go to your LinkedIn messages")
print("2. Copy the sender's name, headline, and message")
print("3. Paste the details below\n")

# Get real data from user
sender_name = input("Sender Name: ").strip()
headline = input("Headline (from their profile): ").strip()
message = input("Message content: ").strip()
email_in_message = input("Email (if provided in message, or press Enter): ").strip()
profile_url = input("LinkedIn Profile URL: ").strip()

# Create message data
message_data = {
    'sender_name': sender_name,
    'headline': headline,
    'message': message,
    'profile_url': profile_url,
    'person_urn': f"real_lead_{sender_name.lower().replace(' ', '_')}"
}

print("\n" + "=" * 70)
print("Processing LinkedIn Lead...")
print("=" * 70)

# Process the lead
result = process_linkedin_message(
    message_id=f"real_{sender_name.lower().replace(' ', '_')}",
    message_data=message_data,
    send_follow_up=True
)

# Print results
print("\n" + "=" * 70)
print("  RESULTS")
print("=" * 70)
print(f"Success: {result.get('success', False)}")
print(f"Customer ID in Odoo: {result.get('customer_id', 'N/A')}")
print(f"Lead Score: {result.get('lead_score', 0)}")
print(f"Follow-up Email Sent: {result.get('follow_up_sent', False)}")

if result.get('success'):
    print("\n[OK] Lead processed successfully!")
    print("\nWhere to check results:")
    print(f"  1. Odoo: http://localhost:8069 → Sales → Customers → ID {result.get('customer_id')}")
    print(f"  2. Lead File: D:\\prompteng\\AI_Employee_Vault\\Leads\\")
    print(f"  3. Gmail Sent: https://mail.google.com → Sent folder")
else:
    print(f"\n[ERROR] {result.get('error', 'Unknown error')}")

print("=" * 70)
