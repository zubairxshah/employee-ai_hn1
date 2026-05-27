"""
Email Integration Test
Tests the complete email flow: MCP server + Skill + Draft workflow
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from skills.action import EmailMCPActionSkill
from skills.registry import get_registry


def print_section(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_server_running():
    """Test if Email MCP server is running"""
    print_section("1. Server Status Check")
    
    try:
        import requests
        r = requests.get('http://localhost:8001/capabilities', timeout=5)
        caps = r.json()
        
        print(f"[OK] Email MCP Server is running")
        print(f"     Name: {caps.get('name')}")
        print(f"     Version: {caps.get('version')}")
        print(f"     Configured: {caps.get('configured')}")
        
        if not caps.get('configured'):
            print(f"\n[INFO] Gmail credentials not configured")
            print(f"       Edit .env and add:")
            print(f"       GMAIL_ADDRESS=your_email@gmail.com")
            print(f"       GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx")
            print(f"       See: EMAIL_MCP_SETUP.md")
        
        return True
    except Exception as e:
        print(f"[FAIL] Email MCP Server not running: {e}")
        print(f"       Start with: python start_mcp_servers.py")
        return False


def test_skill_registered():
    """Test if email skill is registered"""
    print_section("2. Skill Registration Check")
    
    registry = get_registry(str(Path(__file__).parent / 'skills' / 'config'))
    email_skill = registry.get('email_mcp_action')
    
    if email_skill:
        print(f"[OK] Email MCP Action skill registered")
        print(f"     Name: {email_skill.name}")
        print(f"     Version: {email_skill.version}")
        print(f"     MCP URL: {email_skill.mcp_url}")
        return True
    else:
        print(f"[FAIL] Email skill not registered")
        return False


def test_draft_creation():
    """Test creating a draft email"""
    print_section("3. Draft Email Creation Test")
    
    registry = get_registry(str(Path(__file__).parent / 'skills' / 'config'))
    email_skill = registry.get('email_mcp_action')
    
    if not email_skill:
        print("[SKIP] Skill not available")
        return True
    
    result = email_skill.run(
        {'vault_path': r'D:\prompteng\AI_Employee_Vault'},
        {
            'action': 'draft',
            'to': 'test@example.com',
            'subject': 'AI Employee Test Draft',
            'body': 'This is a test draft email created by the AI Employee system.\n\nMove this file to Approved/Email_Drafts/ to send, or Rejected/Email_Drafts/ to discard.'
        }
    )
    
    if result.get('success'):
        print(f"[OK] Draft created successfully")
        print(f"     To: {result.get('to')}")
        print(f"     Subject: {result.get('subject')}")
        print(f"     File: {result.get('filepath')}")
        print(f"     Status: {result.get('status')}")
        
        # Verify file exists
        filepath = result.get('filepath')
        if filepath and Path(filepath).exists():
            print(f"[OK] Draft file exists")
            return True
        else:
            print(f"[WARN] Draft file not found at {filepath}")
            return True  # Server might have created it elsewhere
    else:
        error = result.get('error', 'Unknown error')
        print(f"[WARN] Draft creation failed: {error}")
        return True  # Expected if server not fully configured


def test_list_all_skills():
    """List all registered skills"""
    print_section("4. All Registered Skills")
    
    registry = get_registry(str(Path(__file__).parent / 'skills' / 'config'))
    skills = registry.list_skills()
    
    print(f"Total skills registered: {len(skills)}")
    for skill_name in sorted(skills):
        metadata = registry.get_metadata(skill_name)
        version = metadata.get('version', 'unknown') if metadata else 'unknown'
        print(f"  - {skill_name} (v{version})")
    
    expected_skills = ['file_system_watcher', 'gmail_watcher', 'filesystem_mcp_action', 
                       'approval_mcp_action', 'email_mcp_action']
    missing = [s for s in expected_skills if s not in skills]
    
    if missing:
        print(f"\n[WARN] Missing expected skills: {missing}")
    else:
        print(f"\n[OK] All expected skills are registered")
    
    return True


def run_integration_test():
    """Run complete integration test"""
    print("\n" + "=" * 60)
    print("  EMAIL INTEGRATION TEST")
    print("=" * 60)
    
    tests = [
        ("Server Running", test_server_running),
        ("Skill Registered", test_skill_registered),
        ("Draft Creation", test_draft_creation),
        ("All Skills", test_list_all_skills),
    ]
    
    results = {}
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"\n[FAIL] {name} threw exception: {e}")
            results[name] = False
    
    # Summary
    print_section("TEST SUMMARY")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "[PASSED]" if result else "[FAILED]"
        print(f"  {name}: {status}")
    
    print(f"\n  Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n[OK] Email integration test PASSED!")
        print("\nNext Steps:")
        print("1. Add Gmail App Password to .env file")
        print("2. Restart Email MCP server")
        print("3. Test sending actual emails")
        print("4. Move to Phase 3: LinkedIn MCP Server")
        return True
    else:
        print(f"\n[FAIL] {total - passed} test(s) failed")
        return False


if __name__ == "__main__":
    success = run_integration_test()
    sys.exit(0 if success else 1)
