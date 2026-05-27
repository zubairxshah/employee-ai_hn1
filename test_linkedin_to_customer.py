"""
Test LinkedIn to Customer Workflow
Tests the complete flow from LinkedIn message to Odoo customer
"""

import json
from linkedin_to_customer_workflow import process_linkedin_message

# Test cases
test_leads = [
    {
        'name': 'Hot Lead - High Intent',
        'message_id': 'test_hot_001',
        'data': {
            'sender_name': 'Michael Chen',
            'headline': 'CEO at StartupXYZ',
            'message': 'Hi! I need your services urgently. We have a budget of $10K and want to get started this month. Please call me at +1-555-0199 or email michael@startupxyz.com.',
            'profile_url': 'https://linkedin.com/in/michaelchen',
            'person_urn': 'michael_chen_456'
        }
    },
    {
        'name': 'Warm Lead - Interested',
        'message_id': 'test_warm_002',
        'data': {
            'sender_name': 'Emily Rodriguez',
            'headline': 'Marketing Manager at GrowthCo',
            'message': 'Hello! I came across your profile and would like to learn more about your offerings. Let\'s schedule a call to discuss potential opportunities.',
            'profile_url': 'https://linkedin.com/in/emilyrodriguez',
            'person_urn': 'emily_rodriguez_789'
        }
    },
    {
        'name': 'Cold Lead - General Connection',
        'message_id': 'test_cold_003',
        'data': {
            'sender_name': 'John Networker',
            'headline': 'Professional at BigCorp',
            'message': 'Thanks for connecting! Looking forward to staying in touch.',
            'profile_url': 'https://linkedin.com/in/johnnetworker',
            'person_urn': 'john_networker_012'
        }
    },
    {
        'name': 'Lead with Company Info',
        'message_id': 'test_company_004',
        'data': {
            'sender_name': 'Lisa Thompson',
            'headline': 'VP of Sales | Enterprise Solutions Inc.',
            'message': 'Interested in exploring a partnership. Our company is looking for technology solutions. Contact: lisa@enterprise-solutions.com',
            'profile_url': 'https://linkedin.com/in/lisathompson',
            'person_urn': 'lisa_thompson_345'
        }
    }
]


def run_tests():
    """Run all test cases"""
    print("=" * 70)
    print("  LINKEDIN TO CUSTOMER WORKFLOW - TEST SUITE")
    print("=" * 70)
    
    results = {
        'passed': 0,
        'failed': 0,
        'total': len(test_leads)
    }
    
    for i, test in enumerate(test_leads, 1):
        print(f"\n{'='*70}")
        print(f"TEST {i}/{results['total']}: {test['name']}")
        print(f"{'='*70}")
        
        try:
            result = process_linkedin_message(
                message_id=test['message_id'],
                message_data=test['data'],
                send_follow_up=True
            )
            
            if result.get('success'):
                print(f"\n[PASS] Test passed")
                print(f"   Customer ID: {result.get('customer_id')}")
                print(f"   Lead Score: {result.get('lead_score')}")
                print(f"   Follow-up Sent: {result.get('follow_up_sent')}")
                
                # Validate lead scoring
                if 'Hot' in test['name'] and result.get('lead_score', 0) >= 80:
                    print(f"   [OK] Correctly scored as HOT lead")
                elif 'Warm' in test['name'] and 50 <= result.get('lead_score', 0) < 80:
                    print(f"   [OK] Correctly scored as WARM lead")
                elif 'Cold' in test['name'] and result.get('lead_score', 0) < 50:
                    print(f"   [OK] Correctly scored as COLD lead")
                
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


def test_lead_scoring():
    """Test lead scoring logic specifically"""
    print("\n" + "=" * 70)
    print("  LEAD SCORING VALIDATION")
    print("=" * 70)
    
    from linkedin_to_customer_workflow import LinkedInLeadWorkflow
    
    workflow = LinkedInLeadWorkflow()
    
    test_cases = [
        {
            'message': 'I need your services urgently, budget $10K, want pricing and proposal',
            'expected_min': 60,
            'description': 'High intent keywords'
        },
        {
            'message': 'Would like to learn more and discuss opportunity',
            'expected_min': 30,
            'description': 'Medium intent keywords'
        },
        {
            'message': 'Thanks for connecting',
            'expected_min': 20,
            'description': 'Base score only'
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        score, keywords, interests = workflow._calculate_lead_score(test['message'], '')
        
        if score >= test['expected_min']:
            print(f"[PASS] Test {i}: {test['description']} - Score: {score}")
        else:
            print(f"[FAIL] Test {i}: {test['description']} - Score: {score} (expected >= {test['expected_min']})")
    
    print("=" * 70)


if __name__ == "__main__":
    # Run main tests
    run_tests()
    
    # Test lead scoring
    test_lead_scoring()
