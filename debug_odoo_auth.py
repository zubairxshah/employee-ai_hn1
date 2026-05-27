"""
Debug Odoo MCP Authentication
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

# Odoo Configuration from .env
ODOO_URL = os.getenv('ODOO_URL', 'http://localhost:8069')
ODOO_DB = os.getenv('ODOO_DB', 'odoo')
ODOO_USERNAME = os.getenv('ODOO_USERNAME', 'admin')
ODOO_PASSWORD = os.getenv('ODOO_PASSWORD', 'admin')

print(f"ODOO_URL: {ODOO_URL}")
print(f"ODOO_DB: {ODOO_DB}")
print(f"ODOO_USERNAME: {ODOO_USERNAME}")
print(f"ODOO_PASSWORD: {ODOO_PASSWORD}")

# Test authentication
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

print(f"\nSending authentication request to {ODOO_URL}/web/session/authenticate")
print(f"Payload: {payload}")

response = requests.post(
    f"{ODOO_URL}/web/session/authenticate",
    json=payload,
    headers={'Content-Type': 'application/json'}
)

result = response.json()
print(f"\nResponse: {result}")

if result.get('result', {}).get('uid'):
    print(f"\n[PASS] Authentication successful!")
    print(f"User ID: {result['result']['uid']}")
    print(f"Username: {result['result'].get('username', 'N/A')}")
else:
    print(f"\n[FAIL] Authentication failed!")
    if 'error' in result:
        print(f"Error: {result['error'].get('message', 'Unknown error')}")
