"""
Test Odoo Integration
Tests the Odoo MCP server and Agent Skill

Gold Tier Feature
"""

import requests
import json
from datetime import datetime


def test_health():
    """Test Odoo MCP health endpoint"""
    print("\n" + "=" * 60)
    print("TEST 1: Health Check")
    print("=" * 60)
    
    try:
        response = requests.get('http://localhost:8005/health', timeout=10)
        result = response.json()
        
        print(f"Status: {result.get('status', 'unknown')}")
        print(f"Odoo Connected: {result.get('odoo_connected', False)}")
        print(f"Odoo URL: {result.get('odoo_url', 'N/A')}")
        print(f"Database: {result.get('database', 'N/A')}")
        print(f"User ID: {result.get('user_id', 'N/A')}")
        
        if result.get('odoo_connected'):
            print("[PASS] Health check PASSED")
            return True
        else:
            print("[WARN] Odoo not connected (server may need configuration)")
            return False

    except requests.exceptions.ConnectionError:
        print("[FAIL] Cannot connect to Odoo MCP server")
        print("   Make sure to run: python start_mcp_servers.py")
        return False
    except Exception as e:
        print(f"[FAIL] {e}")
        return False


def test_authenticate():
    """Test Odoo authentication"""
    print("\n" + "=" * 60)
    print("TEST 2: Authentication")
    print("=" * 60)
    
    try:
        response = requests.post('http://localhost:8005/authenticate', timeout=10)
        result = response.json()
        
        if result.get('success'):
            print(f"[PASS] Authentication PASSED")
            print(f"   User ID: {result.get('user_id')}")
            return True
        else:
            print(f"[WARN] Authentication failed: {result.get('error', 'Unknown error')}")
            return False

    except Exception as e:
        print(f"[FAIL] {e}")
        return False


def test_get_customers():
    """Test getting customers"""
    print("\n" + "=" * 60)
    print("TEST 3: Get Customers")
    print("=" * 60)
    
    try:
        response = requests.post(
            'http://localhost:8005/get_customers',
            json={'limit': 5},
            timeout=10
        )
        result = response.json()
        
        if result.get('success'):
            customers = result.get('customers', [])
            print(f"[PASS] Get Customers PASSED")
            print(f"   Found {result.get('count', 0)} customers")
            
            if customers:
                print("\n   Sample customers:")
                for customer in customers[:3]:
                    name = customer.get('name', 'N/A')
                    email = customer.get('email', 'N/A')
                    print(f"   - {name} ({email})")
            return True
        else:
            print(f"[WARN]  Get customers failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"[FAIL] FAILED: {e}")
        return False


def test_create_customer():
    """Test creating a customer"""
    print("\n" + "=" * 60)
    print("TEST 4: Create Customer")
    print("=" * 60)
    
    try:
        customer_data = {
            "name": f"Test Customer {datetime.now().strftime('%Y%m%d%H%M%S')}",
            "email": f"test{datetime.now().strftime('%Y%m%d%H%M%S')}@example.com"
        }
        
        response = requests.post(
            'http://localhost:8005/create_customer',
            json=customer_data,
            timeout=10
        )
        result = response.json()
        
        if result.get('success'):
            print(f"[PASS] Create Customer PASSED")
            print(f"   Customer ID: {result.get('customer_id')}")
            print(f"   Name: {customer_data['name']}")
            return True, result.get('customer_id')
        else:
            print(f"[WARN]  Create customer failed: {result.get('error', 'Unknown error')}")
            return False, None
            
    except Exception as e:
        print(f"[FAIL] FAILED: {e}")
        return False, None


def test_get_products():
    """Test getting products"""
    print("\n" + "=" * 60)
    print("TEST 5: Get Products")
    print("=" * 60)
    
    try:
        response = requests.post(
            'http://localhost:8005/get_products',
            json={'limit': 5},
            timeout=10
        )
        result = response.json()
        
        if result.get('success'):
            products = result.get('products', [])
            print(f"[PASS] Get Products PASSED")
            print(f"   Found {result.get('count', 0)} products")
            
            if products:
                print("\n   Sample products:")
                for product in products[:3]:
                    name = product.get('name', 'N/A')
                    price = product.get('list_price', 0)
                    type_ = product.get('type', 'N/A')
                    print(f"   - {name} (${price} - {type_})")
            return True
        else:
            print(f"[WARN]  Get products failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"[FAIL] FAILED: {e}")
        return False


def test_create_product():
    """Test creating a product"""
    print("\n" + "=" * 60)
    print("TEST 6: Create Product")
    print("=" * 60)
    
    try:
        product_data = {
            "name": f"Test Service {datetime.now().strftime('%Y%m%d%H%M%S')}",
            "type": "service",
            "list_price": 100.00,
            "description": "Test service for Gold Tier testing"
        }
        
        response = requests.post(
            'http://localhost:8005/create_product',
            json=product_data,
            timeout=10
        )
        result = response.json()
        
        if result.get('success'):
            print(f"[PASS] Create Product PASSED")
            print(f"   Product ID: {result.get('product_id')}")
            print(f"   Name: {product_data['name']}")
            print(f"   Price: ${product_data['list_price']}")
            return True, result.get('product_id')
        else:
            print(f"[WARN]  Create product failed: {result.get('error', 'Unknown error')}")
            return False, None
            
    except Exception as e:
        print(f"[FAIL] FAILED: {e}")
        return False, None


def test_get_invoices():
    """Test getting invoices"""
    print("\n" + "=" * 60)
    print("TEST 7: Get Invoices")
    print("=" * 60)
    
    try:
        response = requests.post(
            'http://localhost:8005/get_invoices',
            json={'state': 'posted', 'limit': 10},
            timeout=10
        )
        result = response.json()
        
        if result.get('success'):
            print(f"[PASS] Get Invoices PASSED")
            print(f"   Found {result.get('count', 0)} invoices")
            return True
        else:
            print(f"[WARN]  Get invoices failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"[FAIL] FAILED: {e}")
        return False


def test_get_financial_summary():
    """Test getting financial summary"""
    print("\n" + "=" * 60)
    print("TEST 8: Get Financial Summary")
    print("=" * 60)
    
    try:
        response = requests.post(
            'http://localhost:8005/get_financial_summary',
            json={},
            timeout=10
        )
        result = response.json()
        
        if result.get('success'):
            summary = result.get('summary', {})
            print(f"[PASS] Get Financial Summary PASSED")
            
            receivables = summary.get('receivables', {})
            payables = summary.get('payables', {})
            
            print(f"\n   Receivables:")
            print(f"   - Total Invoiced: ${receivables.get('total_invoiced', 0):,.2f}")
            print(f"   - Total Outstanding: ${receivables.get('total_outstanding', 0):,.2f}")
            print(f"   - Invoice Count: {receivables.get('invoice_count', 0)}")
            
            print(f"\n   Payables:")
            print(f"   - Total Billed: ${payables.get('total_billed', 0):,.2f}")
            print(f"   - Total Outstanding: ${payables.get('total_outstanding', 0):,.2f}")
            print(f"   - Bill Count: {payables.get('bill_count', 0)}")
            
            print(f"\n   Net Position: ${summary.get('net_position', 0):,.2f}")
            
            return True
        else:
            print(f"[WARN]  Get financial summary failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"[FAIL] FAILED: {e}")
        return False


def test_agent_skill():
    """Test Odoo Agent Skill"""
    print("\n" + "=" * 60)
    print("TEST 9: Odoo Agent Skill")
    print("=" * 60)

    try:
        # Import skill module to trigger auto-registration
        from skills.action import OdooMCPActionSkill
        from skills.registry import get_skill

        # Get Odoo skill
        odoo_skill = get_skill('odoo_mcp_action')
        
        if not odoo_skill:
            print("[WARN]  Odoo skill not found")
            return False
        
        print(f"[PASS] Odoo Skill Loaded")
        print(f"   Name: odoo_mcp_action")
        print(f"   Version: {odoo_skill.version}")
        print(f"   Description: {odoo_skill.get_capability_description()}")
        
        # Test health check via skill
        result = odoo_skill.run(
            context={},
            parameters={'action': 'health'}
        )
        
        if result.get('success') or 'odoo_connected' in result:
            print(f"[PASS] Skill Health Check PASSED")
            return True
        else:
            print(f"[WARN]  Skill health check failed: {result.get('error', 'Unknown error')}")
            return False
            
    except ImportError:
        print("[FAIL] FAILED: Cannot import skills module")
        return False
    except Exception as e:
        print(f"[FAIL] FAILED: {e}")
        return False


def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("  ODOO INTEGRATION TEST SUITE - GOLD TIER")
    print("=" * 70)
    print("\nThis test suite verifies the Odoo MCP server and Agent Skill.")
    print("Note: Some tests require Odoo to be installed and configured.\n")
    
    results = {
        'passed': 0,
        'failed': 0,
        'skipped': 0
    }
    
    # Test 1: Health Check
    if test_health():
        results['passed'] += 1
    else:
        results['failed'] += 1
        print("\n[WARN]  Skipping remaining tests (Odoo not connected)")
        return results
    
    # Test 2: Authentication
    if test_authenticate():
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Test 3: Get Customers
    if test_get_customers():
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Test 4: Create Customer
    success, _ = test_create_customer()
    if success:
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Test 5: Get Products
    if test_get_products():
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Test 6: Create Product
    success, _ = test_create_product()
    if success:
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Test 7: Get Invoices
    if test_get_invoices():
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Test 8: Get Financial Summary
    if test_get_financial_summary():
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Test 9: Agent Skill
    if test_agent_skill():
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Print summary
    print("\n" + "=" * 70)
    print("  TEST SUMMARY")
    print("=" * 70)
    print(f"  Total Tests: {results['passed'] + results['failed']}")
    print(f"  Passed: {results['passed']}")
    print(f"  Failed: {results['failed']}")
    print(f"  Success Rate: {results['passed']/(results['passed']+results['failed'])*100:.1f}%")
    print("=" * 70)
    
    if results['failed'] == 0:
        print("\n[SUCCESS] ALL TESTS PASSED! Odoo integration is working correctly.")
    else:
        print(f"\n[WARN]  {results['failed']} test(s) failed. Review the output above.")
    
    return results


if __name__ == "__main__":
    run_all_tests()
