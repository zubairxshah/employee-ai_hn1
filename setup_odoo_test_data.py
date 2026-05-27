"""
Setup Odoo Test Data
Installs required modules and creates test data via Odoo API
"""

import requests
import json

ODOO_URL = "http://localhost:8069"
ODOO_DB = "odoo"
ODOO_USERNAME = "admin"
ODOO_PASSWORD = "admin123"

session = requests.Session()


def authenticate():
    """Authenticate with Odoo"""
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
    
    response = session.post(
        f"{ODOO_URL}/web/session/authenticate",
        json=payload,
        headers={'Content-Type': 'application/json'}
    )
    result = response.json()
    
    if result.get('result', {}).get('uid'):
        print(f"[PASS] Authenticated as: {result['result'].get('name', 'Unknown')}")
        return True
    else:
        print(f"[FAIL] Authentication failed")
        return False


def install_module(module_name):
    """Install an Odoo module"""
    print(f"\nInstalling module: {module_name}")
    
    # First, check if module exists
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "model": "ir.module.module",
            "method": "search_read",
            "args": [[["name", "=", module_name]], ["name", "state", "summary"]]
        },
        "id": 2
    }
    
    response = session.post(
        f"{ODOO_URL}/jsonrpc",
        json=payload,
        headers={'Content-Type': 'application/json'}
    )
    result = response.json()
    
    if 'error' in result:
        print(f"  [WARN] Module {module_name} not found: {result['error']}")
        return False
    
    modules = result.get('result', [])
    if not modules:
        print(f"  [WARN] Module {module_name} not found")
        return False
    
    module = modules[0]
    state = module.get('state', 'uninstalled')
    
    if state == 'installed':
        print(f"  [INFO] Module {module_name} already installed")
        return True
    
    # Install the module
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "model": "ir.module.module",
            "method": "button_immediate_install",
            "args": [[module['id']]]
        },
        "id": 3
    }
    
    response = session.post(
        f"{ODOO_URL}/jsonrpc",
        json=payload,
        headers={'Content-Type': 'application/json'}
    )
    result = response.json()
    
    if 'error' in result:
        print(f"  [FAIL] Installation failed: {result['error']}")
        return False
    
    print(f"  [PASS] Module {module_name} installed")
    return True


def create_test_data():
    """Create test customers, products, and invoices"""
    
    print("\n" + "="*60)
    print("Creating Test Data")
    print("="*60)
    
    # Create Test Customers
    print("\n[1] Creating Customers...")
    customers = [
        {"name": "Acme Corporation", "email": "contact@acme.com", "phone": "+1-555-0100"},
        {"name": "Global Tech Inc", "email": "info@globaltech.com", "phone": "+1-555-0200"},
        {"name": "Sunrise Solutions", "email": "hello@sunrise.com", "phone": "+1-555-0300"},
    ]
    
    for customer in customers:
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "model": "res.partner",
                "method": "create",
                "args": [customer]
            },
            "id": 10
        }
        
        response = session.post(
            f"{ODOO_URL}/jsonrpc",
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        result = response.json()
        
        if 'result' in result:
            print(f"  [PASS] Created customer: {customer['name']} (ID: {result['result']})")
        else:
            print(f"  [WARN] Failed to create {customer['name']}")
    
    # Create Test Products
    print("\n[2] Creating Products...")
    products = [
        {"name": "Consulting Service", "type": "service", "list_price": 150.00, "description": "Professional consulting services"},
        {"name": "Software License", "type": "product", "list_price": 500.00, "description": "Annual software license"},
        {"name": "Support Package", "type": "service", "list_price": 200.00, "description": "Monthly support package"},
        {"name": "Training Session", "type": "service", "list_price": 300.00, "description": "On-site training session"},
    ]
    
    for product in products:
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "model": "product.template",
                "method": "create",
                "args": [product]
            },
            "id": 20
        }
        
        response = session.post(
            f"{ODOO_URL}/jsonrpc",
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        result = response.json()
        
        if 'result' in result:
            print(f"  [PASS] Created product: {product['name']} (ID: {result['result']})")
        else:
            print(f"  [WARN] Failed to create {product['name']}")
    
    # Create Test Invoices
    print("\n[3] Creating Invoices...")
    
    # Get customer ID
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "model": "res.partner",
            "method": "search_read",
            "args": [[["name", "=", "Acme Corporation"]], []],
            "kwargs": {"limit": 1}
        },
        "id": 30
    }
    
    response = session.post(f"{ODOO_URL}/jsonrpc", json=payload, headers={'Content-Type': 'application/json'})
    result = response.json()
    
    if result.get('result'):
        partner_id = result['result'][0]['id']
        
        # Create invoice
        invoice = {
            "move_type": "out_invoice",
            "partner_id": partner_id,
            "invoice_line_ids": [
                (0, 0, {
                    "name": "Consulting Services",
                    "quantity": 10,
                    "price_unit": 150.00
                })
            ]
        }
        
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "model": "account.move",
                "method": "create",
                "args": [invoice]
            },
            "id": 31
        }
        
        response = session.post(f"{ODOO_URL}/jsonrpc", json=payload, headers={'Content-Type': 'application/json'})
        result = response.json()
        
        if 'result' in result:
            print(f"  [PASS] Created invoice (ID: {result['result']})")
            
            # Post the invoice
            payload = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "model": "account.move",
                    "method": "action_post",
                    "args": [[result['result']]]
                },
                "id": 32
            }
            
            response = session.post(f"{ODOO_URL}/jsonrpc", json=payload, headers={'Content-Type': 'application/json'})
            print(f"  [PASS] Invoice posted")
        else:
            print(f"  [WARN] Failed to create invoice: {result}")
    else:
        print(f"  [WARN] Could not find customer for invoice")
    
    print("\n" + "="*60)
    print("Test data creation complete!")
    print("="*60)


def main():
    print("="*60)
    print("Odoo Test Data Setup")
    print("="*60)
    
    if not authenticate():
        print("[FAIL] Could not authenticate. Exiting.")
        return
    
    # Install required modules
    print("\n" + "="*60)
    print("Installing Required Modules")
    print("="*60)
    
    modules = [
        "sale",           # Sales Management
        "account",        # Accounting/Invoicing
        "product",        # Product Management
    ]
    
    for module in modules:
        install_module(module)
    
    # Create test data
    create_test_data()
    
    print("\n[INFO] You can now run the integration tests again:")
    print("   python test_odoo_integration.py")


if __name__ == "__main__":
    main()
