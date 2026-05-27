"""
Manual Email Sender - Process approved files manually
"""

import os
import requests
from pathlib import Path

VAULT_PATH = r"D:\prompteng\AI_Employee_Vault"
APPROVED_DIR = os.path.join(VAULT_PATH, "Approved")
DONE_DIR = os.path.join(VAULT_PATH, "Done")
EMAIL_MCP_URL = "http://localhost:8001"

print("=" * 70)
print("   MANUAL EMAIL PROCESSOR")
print("=" * 70)

# Find all .md files in Approved
approved_files = []
for filename in os.listdir(APPROVED_DIR):
    if filename.endswith('.md') and not filename.startswith('.'):
        filepath = os.path.join(APPROVED_DIR, filename)
        if os.path.isfile(filepath):
            approved_files.append((filename, filepath))

if not approved_files:
    print("\nNo files found in Approved folder.")
    exit(0)

print(f"\nFound {len(approved_files)} file(s) in Approved/:")
for filename, _ in approved_files:
    print(f"  - {filename}")

print("\nProcessing...")
print("-" * 70)

for filename, filepath in approved_files:
    print(f"\nProcessing: {filename}")
    
    # Read file content
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract email details from frontmatter
        to_email = None
        subject = None
        body = None
        
        for line in content.split('\n'):
            if line.startswith('recipient:'):
                to_email = line.split(':', 1)[1].strip()
            elif line.startswith('reason:'):
                subject = f"Invoice: {line.split(':', 1)[1].strip()}"
        
        # Use default if not found
        if not to_email:
            to_email = "emaxis.newsletter@gmail.com"
        if not subject:
            subject = "Invoice from AI Employee"
        
        body = f"""Dear Valued Client,

This email was processed automatically by your AI Employee system.

File: {filename}
Status: Approved and processed

Best regards,
AI Employee System
"""
        
        # Send via Email MCP
        print(f"  To: {to_email}")
        print(f"  Subject: {subject}")
        
        email_data = {
            "to": to_email,
            "subject": subject,
            "body": body
        }
        
        response = requests.post(f"{EMAIL_MCP_URL}/send_email", json=email_data, timeout=30)
        result = response.json()
        
        if result.get('success'):
            print(f"  [OK] Email sent successfully!")
            
            # Move to Done
            done_path = os.path.join(DONE_DIR, filename)
            os.rename(filepath, done_path)
            print(f"  [OK] File moved to Done/")
        else:
            print(f"  [ERROR] Email send failed: {result}")
            
    except Exception as e:
        print(f"  [ERROR] Failed to process: {e}")

print("\n" + "=" * 70)
print("   PROCESSING COMPLETE")
print("=" * 70)
print("\nCheck your Gmail inbox for the emails!")
print("=" * 70)
