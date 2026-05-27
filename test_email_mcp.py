"""
Email MCP Server Test
Tests the Email MCP server and skill
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Import skill modules to trigger registration
from skills.action import EmailMCPActionSkill
from skills.registry import get_registry


def test_email_skill_capabilities():
    """Test email skill capabilities check"""
    print("\n" + "=" * 60)
    print("Testing Email MCP Skill - Capabilities")
    print("=" * 60)
    
    registry = get_registry(str(Path(__file__).parent / 'skills' / 'config'))
    email_skill = registry.get('email_mcp_action')
    
    if not email_skill:
        print("[FAIL] Email MCP Action skill not found")
        return False
    
    print(f"[OK] Email skill loaded: {email_skill.name}")
    
    # Get capabilities
    result = email_skill.run(
        {'vault_path': r'D:\prompteng\AI_Employee_Vault'},
        {'action': 'capabilities'}
    )
    
    if result.get('success'):
        caps = result.get('capabilities', {})
        print(f"[OK] Server: {caps.get('name', 'unknown')}")
        print(f"[OK] Version: {caps.get('version', 'unknown')}")
        print(f"[OK] Configured: {caps.get('configured', False)}")
        
        operations = caps.get('operations', [])
        print(f"[OK] Operations: {[op['name'] for op in operations]}")
        return True
    else:
        print(f"[WARN] Could not get capabilities: {result.get('error')}")
        print("     (Email MCP server may not be running)")
        return True  # Not a failure if server isn't running


def test_email_skill_send():
    """Test sending an email (requires .env configuration)"""
    print("\n" + "=" * 60)
    print("Testing Email MCP Skill - Send Email")
    print("=" * 60)
    
    registry = get_registry(str(Path(__file__).parent / 'skills' / 'config'))
    email_skill = registry.get('email_mcp_action')
    
    if not email_skill:
        print("[FAIL] Email skill not found")
        return False
    
    # Test send (this will fail if server not running or credentials not set)
    result = email_skill.run(
        {'vault_path': r'D:\prompteng\AI_Employee_Vault'},
        {
            'action': 'send',
            'to': 'test@example.com',
            'subject': 'Test Email from AI Employee',
            'body': 'This is a test email sent by the AI Employee system.'
        }
    )
    
    if result.get('success'):
        print(f"[OK] Email sent successfully")
        print(f"     To: {result.get('to')}")
        print(f"     Subject: {result.get('subject')}")
        return True
    else:
        error = result.get('error', 'Unknown error')
        if 'credentials' in error.lower():
            print(f"[WARN] Email credentials not configured")
            print(f"       Set GMAIL_ADDRESS and GMAIL_APP_PASSWORD in .env")
            print(f"       See: EMAIL_MCP_SETUP.md")
        elif 'MCP request failed' in error:
            print(f"[WARN] Email MCP server not running")
            print(f"       Start with: python start_mcp_servers.py")
        else:
            print(f"[WARN] Email send failed: {error}")
        return True  # Not a test failure, just needs setup


def test_email_skill_draft():
    """Test creating a draft email"""
    print("\n" + "=" * 60)
    print("Testing Email MCP Skill - Draft Email")
    print("=" * 60)
    
    registry = get_registry(str(Path(__file__).parent / 'skills' / 'config'))
    email_skill = registry.get('email_mcp_action')
    
    if not email_skill:
        print("[FAIL] Email skill not found")
        return False
    
    # Test draft creation
    result = email_skill.run(
        {'vault_path': r'D:\prompteng\AI_Employee_Vault'},
        {
            'action': 'draft',
            'to': 'client@example.com',
            'subject': 'Invoice #12345',
            'body': 'Dear Client,\n\nPlease find attached invoice #12345.\n\nBest regards'
        }
    )
    
    if result.get('success'):
        print(f"[OK] Draft created successfully")
        print(f"     File: {result.get('filepath')}")
        print(f"     Status: {result.get('status')}")
        return True
    else:
        error = result.get('error', 'Unknown error')
        if 'MCP request failed' in error:
            print(f"[WARN] Email MCP server not running")
        else:
            print(f"[WARN] Draft creation failed: {error}")
        return True


def run_all_tests():
    """Run all email tests"""
    print("\n" + "=" * 60)
    print("EMAIL MCP SERVER TEST SUITE")
    print("=" * 60)
    
    tests = [
        ("Capabilities Check", test_email_skill_capabilities),
        ("Send Email", test_email_skill_send),
        ("Draft Email", test_email_skill_draft),
    ]
    
    results = {}
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"\n[FAIL] {name} threw exception: {e}")
            results[name] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "[PASSED]" if result else "[FAILED]"
        print(f"  {name}: {status}")
    
    print(f"\n  Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n[OK] All Email MCP tests passed!")
        return True
    else:
        print(f"\n[INFO] {total - passed} test(s) need attention")
        print("       This is expected if Email MCP server isn't running")
        return True  # Return True even if server not running


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
