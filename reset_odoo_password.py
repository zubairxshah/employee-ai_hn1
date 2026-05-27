"""
Reset Odoo Admin Password - JSON-RPC version
"""

import requests
import json

ODOO_URL = "http://localhost:8069"
ODOO_DB = "aiemployee"
ODOO_USERNAME = "admin"

def try_authenticate(password):
    """Try to authenticate with a password"""
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "db": ODOO_DB,
            "login": ODOO_USERNAME,
            "password": password
        },
        "id": 1
    }
    
    response = requests.post(
        f"{ODOO_URL}/web/session/authenticate",
        json=payload,
        headers={'Content-Type': 'application/json'}
    )
    result = response.json()
    
    if result.get('result', {}).get('uid'):
        return result['result']['uid']
    return None

def reset_password(new_password="admin123"):
    """Reset admin password"""
    
    # Try common default passwords
    default_passwords = ["admin", "password", "odoo", "changeme", "", "Admin!123", "admin123"]
    
    print("Testing authentication...")
    
    for pwd in default_passwords:
        uid = try_authenticate(pwd)
        if uid:
            print(f"[SUCCESS] Authenticated with password: '{pwd}'")
            print(f"User ID: {uid}")
            
            # Reset password
            payload = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "model": "res.users",
                    "method": "write",
                    "args": [[uid], {"password": new_password}]
                },
                "id": 2
            }
            
            response = requests.post(
                f"{ODOO_URL}/jsonrpc",
                json=payload,
                headers={'Content-Type': 'application/json'}
            )
            result = response.json()
            
            if 'error' not in result:
                print(f"[SUCCESS] Password reset to: '{new_password}'")
                return new_password
            else:
                print(f"[FAIL] Could not reset password: {result['error']}")
                return None
    
    # Try API key
    print("\nTrying API key authentication...")
    api_key = "2049261ccdb210ea021fbad5a1457e3664c3e617"
    uid = try_authenticate(api_key)
    if uid:
        print(f"[SUCCESS] Authenticated with API key")
        print(f"User ID: {uid}")
        
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "model": "res.users",
                "method": "write",
                "args": [[uid], {"password": new_password}]
            },
            "id": 2
        }
        
        response = requests.post(
            f"{ODOO_URL}/jsonrpc",
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        result = response.json()
        
        if 'error' not in result:
            print(f"[SUCCESS] Password reset to: '{new_password}'")
            return new_password
        else:
            print(f"[FAIL] Could not reset password: {result['error']}")
            return None
    
    print("\n[FAIL] Could not authenticate.")
    print("\nPlease tell me the password you set when creating the Odoo database.")
    print("Or access Odoo at http://localhost:8069 and reset it via the UI.")
    return None

if __name__ == "__main__":
    reset_password()
