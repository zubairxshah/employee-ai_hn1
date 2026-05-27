"""
Gmail OAuth2 Authentication Script
Generates and saves Gmail API credentials
"""

import os
import json
import sys
from pathlib import Path
from datetime import datetime

# Check for required dependencies
try:
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
except ImportError:
    print("Missing required dependencies. Install with:")
    print("  pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
    sys.exit(1)


# Gmail API scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify'
]

# Paths
PROJECT_ROOT = Path(__file__).parent.parent  # Go up one level from scripts/
CREDENTIALS_FILE = PROJECT_ROOT / 'gmail_credentials.json'
TOKEN_FILE = PROJECT_ROOT / '.gmail_token.json'


def authenticate():
    """
    Authenticate with Gmail API and save credentials.
    """
    print("=" * 60)
    print("  Gmail API Authentication")
    print("=" * 60)
    
    # Check if credentials file exists
    if not CREDENTIALS_FILE.exists():
        print(f"\n[ERROR] Credentials file not found: {CREDENTIALS_FILE}")
        print("\nTo get credentials:")
        print("1. Follow the guide in GMAIL_SETUP.md")
        print("2. Download OAuth2 credentials from Google Cloud Console")
        print(f"3. Save as: {CREDENTIALS_FILE}")
        return False
    
    # Load credentials
    print(f"\n[OK] Found credentials file: {CREDENTIALS_FILE}")
    
    creds = None
    
    # Try to load existing token
    if TOKEN_FILE.exists():
        print("Loading existing token...")
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
            print("[OK] Token loaded successfully")
        except Exception as e:
            print(f"[WARN] Could not load token: {e}")
            creds = None
    
    # Refresh or authenticate
    if creds and creds.expired:
        print("Token expired, refreshing...")
        if creds.refresh_token:
            try:
                creds.refresh(Request())
                print("[OK] Token refreshed successfully")
            except Exception as e:
                print(f"[WARN] Token refresh failed: {e}")
                creds = None
    
    if not creds or not creds.valid:
        print("\nStarting OAuth2 flow...")
        print("1. A browser window will open")
        print("2. Sign in with your Google account")
        print("3. Grant permissions to access Gmail")
        print("4. You'll be redirected back here")
        
        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES
            )
            creds = flow.run_local_server(port=0, open_browser=True)
            print("[OK] Authentication successful!")
        except Exception as e:
            print(f"[ERROR] Authentication failed: {e}")
            return False
    
    # Save the credentials
    print(f"\nSaving token to: {TOKEN_FILE}")
    try:
        with open(TOKEN_FILE, 'w') as f:
            f.write(creds.to_json())
        print("[OK] Token saved successfully")
    except Exception as e:
        print(f"[ERROR] Could not save token: {e}")
        return False
    
    # Test the connection
    print("\nTesting Gmail API connection...")
    try:
        service = build('gmail', 'v1', credentials=creds)
        profile = service.users().getProfile(userId='me').execute()
        email = profile.get('emailAddress')
        print(f"[OK] Connected to Gmail API as: {email}")
    except Exception as e:
        print(f"[ERROR] Gmail API test failed: {e}")
        return False
    
    # Print summary
    print("\n" + "=" * 60)
    print("  Authentication Complete!")
    print("=" * 60)
    print(f"\nCredentials saved to:")
    print(f"  - Token file: {TOKEN_FILE}")
    print(f"\nNext steps:")
    print(f"  1. Update .env with your credentials")
    print(f"  2. Configure skills/config/gmail_watcher.yaml")
    print(f"  3. Run: python test_skills.py")
    
    # Print environment variables to add to .env
    with open(CREDENTIALS_FILE, 'r') as f:
        client_creds = json.load(f)
    
    print(f"\nAdd these to your .env file:")
    print(f"  GMAIL_CLIENT_ID={client_creds.get('installed', {}).get('client_id', '')}")
    print(f"  GMAIL_CLIENT_SECRET={client_creds.get('installed', {}).get('client_secret', '')}")
    
    return True


def test_connection():
    """
    Test Gmail API connection with existing credentials.
    """
    print("Testing Gmail API connection...")
    
    if not TOKEN_FILE.exists():
        print("[ERROR] No token file found. Run authentication first.")
        return False
    
    try:
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        
        if creds.expired and creds.refresh_token:
            print("Token expired, refreshing...")
            creds.refresh(Request())
        
        service = build('gmail', 'v1', credentials=creds)
        profile = service.users().getProfile(userId='me').execute()
        
        print(f"[OK] Connected as: {profile.get('emailAddress')}")
        
        # List recent messages
        results = service.users().messages().list(
            userId='me', 
            maxResults=5,
            q='is:unread'
        ).execute()
        
        messages = results.get('messages', [])
        print(f"[OK] Found {len(messages)} unread messages")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Connection test failed: {e}")
        return False


def main():
    """Main entry point"""
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        success = test_connection()
    else:
        success = authenticate()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
