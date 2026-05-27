"""
Debug Odoo MCP Errors
"""

import requests
import json

ODOO_URL = "http://localhost:8069"
ODOO_DB = "odoo"
ODOO_USERNAME = "admin"
ODOO_PASSWORD = "admin"

session = requests.Session()

# Authenticate
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

if not result.get('result', {}).get('uid'):
    print("Authentication failed!")
    print(json.dumps(result, indent=2))
    exit(1)

print(f"Authenticated as: {result['result'].get('name', 'Unknown')}")
print(f"User ID: {result['result']['uid']}")

# Test 1: Try to get partners (customers)
print("\n" + "="*60)
print("Test 1: Get Partners (res.partner)")
print("="*60)

payload = {
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
        "model": "res.partner",
        "method": "search_read",
        "args": [[["customer_rank", ">", 0]]],
        "kwargs": {"limit": 5}
    },
    "id": 2
}

response = session.post(f"{ODOO_URL}/jsonrpc", json=payload)
result = response.json()

if 'error' in result:
    print(f"Error with customer_rank filter:")
    print(f"  {result['error'].get('message', 'Unknown')}")
else:
    print(f"Success! Found {len(result.get('result', []))} customers")
    for c in result.get('result', []):
        print(f"  - {c.get('name')}")

# Test 2: Try without filter
print("\n" + "="*60)
print("Test 2: Get All Partners (no filter)")
print("="*60)

payload = {
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
        "model": "res.partner",
        "method": "search_read",
        "args": [[]],
        "kwargs": {"limit": 10}
    },
    "id": 3
}

response = session.post(f"{ODOO_URL}/jsonrpc", json=payload)
result = response.json()

if 'error' in result:
    print(f"Error:")
    print(f"  {result['error'].get('message', 'Unknown')}")
else:
    print(f"Success! Found {len(result.get('result', []))} partners")
    for c in result.get('result', [])[:5]:
        print(f"  - {c.get('name')} (customer_rank: {c.get('customer_rank', 'N/A')})")

# Test 3: Check installed modules
print("\n" + "="*60)
print("Test 3: Check Installed Modules")
print("="*60)

payload = {
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
        "model": "ir.module.module",
        "method": "search_read",
        "args": [[["state", "=", "installed"]], ["name", "summary"]],
        "kwargs": {"limit": 50}
    },
    "id": 4
}

response = session.post(f"{ODOO_URL}/jsonrpc", json=payload)
result = response.json()

if 'error' in result:
    print(f"Error checking modules:")
    print(f"  {result['error'].get('message', 'Unknown')}")
else:
    modules = result.get('result', [])
    print(f"Installed modules ({len(modules)}):")
    for m in modules[:20]:
        print(f"  - {m.get('name')}: {m.get('summary', '')[:50]}")
    if len(modules) > 20:
        print(f"  ... and {len(modules) - 20} more")

# Test 4: Check if res.partner has customer_rank field
print("\n" + "="*60)
print("Test 4: Check partner fields")
print("="*60)

payload = {
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
        "model": "ir.model.fields",
        "method": "search_read",
        "args": [[["model", "=", "res.partner"], ["name", "=", "customer_rank"]]],
        "kwargs": {"limit": 1}
    },
    "id": 5
}

response = session.post(f"{ODOO_URL}/jsonrpc", json=payload)
result = response.json()

if result.get('result'):
    print("Field 'customer_rank' exists in res.partner")
else:
    print("Field 'customer_rank' DOES NOT exist - Sales module not installed!")
