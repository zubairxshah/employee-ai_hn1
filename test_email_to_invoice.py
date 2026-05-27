"""
Test Email to Invoice Workflow
Tests the complete flow from email to Odoo invoice with approval
"""

import requests
import json
from email_to_invoice_workflow import process_email_message

# Test cases
test_emails = [
    {
        'name': 'Invoice over threshold (requires approval)',
        'message_id': 'test_approval_001',
        'content': """
        Dear Team,
        
        Please find the invoice details below:
        
        Amount: $2,500.00
        Description: Consulting services for February 2026
        
        Thank you for your business!
        
        Best regards,
        John Doe
        Acme Corporation
        john@acme.com
        """,
        'headers': {
            'from': 'John Doe <john@acme.com>',
            'subject': 'Invoice - February 2026',
        }
    },
    {
        'name': 'Invoice under threshold (auto-confirm)',
        'message_id': 'test_auto_002',
        'content': """
        Hello,
        
        Invoice for services rendered:
        
        Total: $500.00
        For: Website maintenance
        
        Thanks,
        Jane Smith
        Tech Solutions
        jane@techsol.com
        """,
        'headers': {
            'from': 'Jane Smith <jane@techsol.com>',
            'subject': 'Payment for services',
        }
    },
    {
        'name': 'Deal confirmation email',
        'message_id': 'test_deal_003',
        'content': """
        Hi,
        
        This confirms our deal:
        
        Amount: $1,200
        Description: Q1 Marketing Package
        
        Please proceed with the invoice.
        
        Regards,
        Bob Wilson
        Marketing Pro
        bob@marketingpro.com
        """,
        'headers': {
            'from': 'Bob Wilson <bob@marketingpro.com>',
            'subject': 'Deal Confirmation - Q1 Marketing',
        }
    }
]


def run_tests():
    """Run all test cases"""
    print("=" * 70)
    print("  EMAIL TO INVOICE WORKFLOW - TEST SUITE")
    print("=" * 70)
    
    results = {
        'passed': 0,
        'failed': 0,
        'total': len(test_emails)
    }
    
    for i, test in enumerate(test_emails, 1):
        print(f"\n{'='*70}")
        print(f"TEST {i}/{results['total']}: {test['name']}")
        print(f"{'='*70}")
        
        try:
            result = process_email_message(
                message_id=test['message_id'],
                email_content=test['content'],
                email_headers=test['headers']
            )
            
            if result.get('success'):
                print(f"\n[PASS] Test passed")
                print(f"   Customer ID: {result.get('customer_id')}")
                print(f"   Invoice ID: {result.get('invoice_id')}")
                print(f"   Requires Approval: {result.get('requires_approval')}")
                
                if result.get('requires_approval'):
                    print(f"   Approval Request ID: {result.get('approval_request_id')}")
                
                results['passed'] += 1
            else:
                print(f"\n[FAIL] Test failed: {result.get('error', 'Unknown error')}")
                results['failed'] += 1
                
        except Exception as e:
            print(f"\n[FAIL] Exception: {e}")
            results['failed'] += 1
    
    # Print summary
    print("\n" + "=" * 70)
    print("  TEST SUMMARY")
    print("=" * 70)
    print(f"  Total Tests: {results['total']}")
    print(f"  Passed: {results['passed']}")
    print(f"  Failed: {results['failed']}")
    print(f"  Success Rate: {results['passed']/results['total']*100:.1f}%")
    print("=" * 70)
    
    if results['failed'] == 0:
        print("\n[SUCCESS] ALL TESTS PASSED!")
    else:
        print(f"\n[WARN] {results['failed']} test(s) failed.")
    
    return results


def test_approval_workflow():
    """Test the approval workflow specifically"""
    print("\n" + "=" * 70)
    print("  APPROVAL WORKFLOW TEST")
    print("=" * 70)
    
    # Create an approval request
    approval_data = {
        'action': 'confirm_invoice',
        'amount': 2500.00,
        'recipient': 'john@acme.com',
        'reason': 'Invoice #25 for John Doe',
        'invoice_id': 25
    }
    
    try:
        response = requests.post(
            'http://localhost:8003/request_approval',
            json=approval_data,
            timeout=30
        )
        result = response.json()
        
        if result.get('success'):
            print(f"[PASS] Approval request created")
            print(f"   Request ID: {result.get('request_id')}")
            print(f"   Filepath: {result.get('filepath')}")
            return True
        else:
            print(f"[FAIL] Approval request failed: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"[FAIL] Exception: {e}")
        return False


if __name__ == "__main__":
    # Run main tests
    run_tests()
    
    # Test approval workflow
    test_approval_workflow()
