"""
LinkedIn OAuth Test Script
Helps troubleshoot and complete the LinkedIn OAuth flow
"""

import requests
import webbrowser
import time
import sys
from pathlib import Path

MCP_URL = "http://localhost:8002"


def check_server():
    """Check if LinkedIn MCP server is running"""
    try:
        response = requests.get(f"{MCP_URL}/capabilities", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("[OK] LinkedIn MCP Server is running")
            print(f"  Name: {data.get('name')}")
            print(f"  Version: {data.get('version')}")
            
            configured = data.get('configured', False)
            authenticated = data.get('authenticated', False)
            
            print(f"  Configured: {'[OK] Yes' if configured else '[FAIL] No'}")
            print(f"  Authenticated: {'[OK] Yes' if authenticated else '[FAIL] No'}")
            
            return True, data
        else:
            print(f"[FAIL] Server returned status {response.status_code}")
            return False, None
    except requests.exceptions.ConnectionError:
        print("[FAIL] LinkedIn MCP Server is NOT running")
        print("\nStart the server with:")
        print("  python start_mcp_servers.py")
        return False, None
    except Exception as e:
        print(f"[FAIL] Error checking server: {e}")
        return False, None


def get_auth_url():
    """Get authorization URL from MCP server"""
    try:
        response = requests.get(f"{MCP_URL}/get_auth_url", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                auth_url = data.get('authorization_url')
                print(f"\n[OK] Authorization URL obtained")
                print(f"\nOpening browser to: {auth_url[:80]}...")
                return auth_url
            else:
                print(f"[FAIL] Error: {data.get('error')}")
                return None
        else:
            print(f"[FAIL] Server error: {response.status_code}")
            return None
    except Exception as e:
        print(f"[FAIL] Error getting auth URL: {e}")
        return None


def open_browser(auth_url):
    """Open authorization URL in browser"""
    print("\n" + "="*60)
    print("NEXT STEPS:")
    print("="*60)
    print("1. Sign in to LinkedIn if prompted")
    print("2. Click 'Authorize' to allow the app")
    print("3. You'll be redirected to a success page")
    print("4. The page will show your token status")
    print("="*60)
    
    print("\nOpening browser now...")
    webbrowser.open(auth_url)
    print("[OK] Browser opened")
    print("Complete the authorization in the browser, then come back here.")
    print("The script will check for the token file automatically.")


def check_token_file():
    """Check if token file exists"""
    token_file = Path(__file__).parent / '.linkedin_token.json'
    
    if token_file.exists():
        import json
        try:
            with open(token_file, 'r') as f:
                token_data = json.load(f)
            
            print(f"\n[OK] Token file found: {token_file}")
            print(f"  Person URN: {token_data.get('person_urn', 'N/A')}")
            print(f"  Expires: {token_data.get('expires_at', 'N/A')}")
            print(f"  Updated: {token_data.get('updated', 'N/A')}")
            
            # Check if token is still valid
            from datetime import datetime
            expires_at = token_data.get('expires_at')
            if expires_at:
                try:
                    expiry = datetime.fromisoformat(expires_at)
                    if datetime.now() < expiry:
                        print(f"  Status: [OK] Token is valid")
                        return True
                    else:
                        print(f"  Status: [FAIL] Token has expired")
                        return False
                except:
                    pass
            
            return True
        except Exception as e:
            print(f"[FAIL] Error reading token file: {e}")
            return False
    else:
        print(f"\n[FAIL] Token file not found: {token_file}")
        return False


def test_create_draft():
    """Test creating a draft post"""
    print("\n" + "="*60)
    print("Testing draft post creation...")
    print("="*60)
    
    try:
        response = requests.post(
            f"{MCP_URL}/create_draft",
            json={
                "text": f"Test post from LinkedIn OAuth script - {time.time()}",
                "visibility": "PUBLIC"
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"[OK] Draft created successfully")
                print(f"  File: {data.get('filename')}")
                print(f"  Path: {data.get('filepath')}")
                return True
            else:
                print(f"[FAIL] Draft creation failed: {data.get('error')}")
                return False
        else:
            print(f"[FAIL] Server error: {response.status_code}")
            print(f"  Response: {response.text}")
            return False
    except Exception as e:
        print(f"[FAIL] Error creating draft: {e}")
        return False


def main():
    """Main OAuth test flow"""
    print("="*60)
    print("LinkedIn OAuth Test & Troubleshooting")
    print("="*60)
    print()
    
    # Step 1: Check server
    print("Step 1: Checking MCP server...")
    server_ok, server_data = check_server()
    
    if not server_ok:
        print("\n[FAIL] Cannot proceed without server running")
        sys.exit(1)
    
    # Step 2: Check if already authenticated
    if server_data and server_data.get('authenticated'):
        print("\n[OK] Already authenticated!")
        
        # Test creating a draft
        if test_create_draft():
            print("\n" + "="*60)
            print("SUCCESS: LinkedIn integration is working!")
            print("="*60)
            sys.exit(0)
        else:
            print("\n[FAIL] Authentication works but posting failed")
            sys.exit(1)
    
    # Step 3: Get authorization URL
    print("\nStep 2: Getting authorization URL...")
    auth_url = get_auth_url()
    
    if not auth_url:
        print("\n[FAIL] Could not get authorization URL")
        print("\nCheck your .env file has:")
        print("  LINKEDIN_CLIENT_ID=your_client_id")
        print("  LINKEDIN_CLIENT_SECRET=your_client_secret")
        sys.exit(1)
    
    # Step 4: Open browser
    print("\nStep 3: Opening browser for authorization...")
    open_browser(auth_url)
    
    # Step 5: Wait and check token
    print("\nStep 4: Waiting for authorization...")
    print("Checking for token file every 2 seconds...")
    
    max_attempts = 30  # Wait up to 60 seconds
    for i in range(max_attempts):
        time.sleep(2)
        if check_token_file():
            print("\n" + "="*60)
            print("[OK] OAuth completed successfully!")
            print("="*60)
            
            # Test creating a draft
            if test_create_draft():
                print("\n" + "="*60)
                print("SUCCESS: LinkedIn integration is fully working!")
                print("="*60)
                sys.exit(0)
            else:
                print("\n[FAIL] Token obtained but posting failed")
                print("Check LinkedIn app permissions")
                sys.exit(1)
    
    print("\n[FAIL] Timeout waiting for authorization")
    print("\nIf you completed authorization but token wasn't saved:")
    print("1. Copy the authorization code from the callback URL")
    print("2. Run: curl -X POST http://localhost:8002/exchange_token -H \"Content-Type: application/json\" -d \"{\\\"code\\\": \\\"YOUR_CODE\\\"}\"")
    sys.exit(1)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n[FAIL] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
