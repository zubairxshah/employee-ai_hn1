"""
Debug Odoo JSON-RPC - Correct format for Odoo 17
Uses XML-RPC which is more reliable
"""

import xmlrpc.client
import json

ODOO_URL = "http://localhost:8069"
ODOO_DB = "odoo"
ODOO_USERNAME = "admin"
ODOO_PASSWORD = "admin"

print("="*60)
print("Testing Odoo 17 API Access")
print("="*60)

# Try XML-RPC (more reliable)
print("\n[1] Testing XML-RPC common endpoint...")
try:
    common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
    uid = common.authenticate(ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD)
    if uid:
        print(f"[PASS] XML-RPC authenticated! User ID: {uid}")
    else:
        print("[FAIL] XML-RPC authentication failed")
except Exception as e:
    print(f"[ERROR] {e}")

print("\n[2] Testing XML-RPC object endpoint (search_read)...")
try:
    common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
    uid = common.authenticate(ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD)
    
    if uid:
        models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
        
        # Search for partners
        partners = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'res.partner', 'search_read',
            [[]],  # domain
            {'limit': 5, 'fields': ['name', 'email']}
        )
        
        if partners:
            print(f"[PASS] Found {len(partners)} partners:")
            for p in partners:
                print(f"  - {p.get('name')} ({p.get('email', 'no email')})")
        else:
            print("[WARN] No partners found (database might be empty)")
            
except Exception as e:
    print(f"[ERROR] {e}")

print("\n[3] Testing JSON-RPC with service parameter...")
import requests

session = requests.Session()

# First authenticate to get session cookie
payload = {
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
        "db": ODOO_DB,
        "login": ODOO_USERNAME,
        "password": ODOO_PASSWORD
    },
    "id": 1
}

response = session.post(f"{ODOO_URL}/web/session/authenticate", json=payload)
result = response.json()

if result.get('result', {}).get('uid'):
    uid = result['result']['uid']
    print(f"[PASS] JSON-RPC authenticated! User ID: {uid}")
    
    # Now use object service with correct format
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "service": "object",
            "method": "execute_kw",
            "args": [
                ODOO_DB,
                uid,
                ODOO_PASSWORD,
                "res.partner",
                "search_read",
                [[]],
                {"limit": 5, "fields": ["name", "email"]}
            ]
        },
        "id": 2
    }
    
    response = session.post(f"{ODOO_URL}/jsonrpc", json=payload)
    result = response.json()
    
    if 'error' in result:
        print(f"[FAIL] {result['error'].get('message', 'Unknown error')}")
    else:
        partners = result.get('result', [])
        if partners:
            print(f"[PASS] Found {len(partners)} partners:")
            for p in partners:
                print(f"  - {p.get('name')}")
        else:
            print("[WARN] No partners found")
else:
    print("[FAIL] JSON-RPC authentication failed")

print("\n" + "="*60)
print("Debug complete!")
print("="*60)
