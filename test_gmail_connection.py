"""Gmail Integration Test"""
from skills.perception import GmailWatcherSkill
from skills.registry import get_registry
from pathlib import Path

# Initialize registry with config
registry = get_registry(str(Path.cwd() / 'skills' / 'config'))
gmail = registry.get('gmail_watcher')

# Get Gmail service info
creds = gmail._get_credentials()
print('=== Gmail Integration Test ===')
print(f'Credentials loaded: {creds is not None}')
print(f'Token valid: {not creds.expired if creds else False}')
print(f'Scopes: {creds.scopes if creds else []}')

# Test Gmail API connection
service = gmail._get_service()
if service:
    # Get profile info
    profile = service.users().getProfile(userId='me').execute()
    print(f'Connected to: {profile.get("emailAddress")}')
    print(f'Messages total: {profile.get("messagesTotal", 0)}')
    print(f'Threads total: {profile.get("threadsTotal", 0)}')
    
    # Check for unread important emails
    results = service.users().messages().list(
        userId='me',
        q='is:unread is:important',
        maxResults=5
    ).execute()
    messages = results.get('messages', [])
    print(f'Unread important emails: {len(messages)}')
    
    print('\n=== Gmail Integration: WORKING ===')
else:
    print('ERROR: Could not connect to Gmail API')
