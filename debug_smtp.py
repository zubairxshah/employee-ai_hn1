"""Debug Gmail SMTP Issue"""
import smtplib
import os

# Read password from .env file
env_path = os.path.join(os.path.dirname(__file__), '.env')
password = None
email = None

with open(env_path, 'r') as f:
    for line in f:
        line = line.strip()
        if line.startswith('GMAIL_ADDRESS='):
            email = line.split('=', 1)[1].strip().strip('"').strip("'")
        elif line.startswith('GMAIL_APP_PASSWORD='):
            password = line.split('=', 1)[1].strip().strip('"').strip("'")

print("=" * 60)
print("GMAIL SMTP DEBUG")
print("=" * 60)
print(f"Email: {email}")
print(f"Password length: {len(password) if password else 0} chars")
print(f"Password: {password[:4]}****{password[-4:]}" if password and len(password) > 8 else "Password not found")
print()

# Check if it's a 16-char app password format
if password:
    clean_pwd = password.replace(' ', '')
    print(f"Password (no spaces): {clean_pwd}")
    print(f"Length (no spaces): {len(clean_pwd)}")
    print(f"Is 16 chars: {len(clean_pwd) == 16}")
print()

# Test SMTP with detailed error
print("Testing SMTP connection...")
try:
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.set_debuglevel(1)  # Enable debug output
    print("\n--- Connecting to server ---")
    server.starttls()
    print("\n--- TLS Started ---")
    
    clean_password = password.replace(' ', '') if password else ''
    print(f"\n--- Attempting login with {email} ---")
    server.login(email, clean_password)
    print("\n[SUCCESS] Login successful!")
    server.quit()
    
except smtplib.SMTPAuthenticationError as e:
    print(f"\n[FAIL] SMTP Authentication Error: {e}")
    print("\nPossible causes:")
    print("1. Password is regular Gmail password (not App Password)")
    print("2. 2-Step Verification is not enabled")
    print("3. App Password was revoked/expired")
    print("4. 'Less secure app access' is blocked (but this shouldn't matter with App Password)")
except Exception as e:
    print(f"\n[FAIL] Error: {e}")
