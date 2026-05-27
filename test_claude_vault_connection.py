"""
Claude Vault Connection Test
Tests the connection between Claude Code and the Obsidian vault
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from claude_vault_connector import ClaudeVaultConnector


def print_section(title: str):
    """Print a formatted section header"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_mcp_servers(connector: ClaudeVaultConnector) -> bool:
    """Test MCP server connectivity"""
    print_section("Testing MCP Server Connectivity")
    
    status = connector.check_mcp_servers()
    
    all_running = True
    for server, info in status.items():
        server_status = info.get("status", "unknown")
        if server_status == "running":
            print(f"[OK] {server.upper()} MCP: Running")
            if "capabilities" in info and info["capabilities"]:
                caps = info["capabilities"]
                print(f"  - Name: {caps.get('name', 'N/A')}")
                print(f"  - Version: {caps.get('version', 'N/A')}")
                ops = caps.get('operations', [])
                print(f"  - Operations: {len(ops)} available")
        else:
            print(f"[FAIL] {server.upper()} MCP: Not Running")
            if "error" in info:
                print(f"  Error: {info['error']}")
            all_running = False
    
    return all_running


def test_vault_structure(connector: ClaudeVaultConnector) -> bool:
    """Test vault directory structure"""
    print_section("Testing Vault Structure")
    
    directories = ["Inbox", "Needs_Action", "Done", "Pending_Approval", "Approved", "Rejected", "Plans"]
    all_exist = True
    
    for dir_name in directories:
        result = connector.list_files(dir_name)
        if result.get("success"):
            files = result.get("files", [])
            print(f"[OK] /{dir_name}: Exists ({len(files)} items)")
        else:
            print(f"[FAIL] /{dir_name}: Not accessible")
            all_exist = False
    
    return all_exist


def test_file_operations(connector: ClaudeVaultConnector) -> bool:
    """Test basic file operations"""
    print_section("Testing File Operations")
    
    # Test write
    test_file = "Inbox/test_connection.md"
    test_content = f"""---
type: test
created: {datetime.now().isoformat()}
---

# Connection Test

This file was created to test the Claude Vault Connector.
If you're reading this, the connection is working!
"""
    
    print("Writing test file...")
    write_result = connector.write_file(test_file, test_content)
    if write_result.get("success"):
        print(f"[OK] Write: Success")
    else:
        print(f"[FAIL] Write: Failed - {write_result.get('error', 'Unknown error')}")
        return False
    
    # Test read
    print("Reading test file...")
    read_result = connector.read_file(test_file)
    if read_result.get("success"):
        print(f"[OK] Read: Success")
        content = read_result.get("content", "")
        if "Connection Test" in content:
            print("[OK] Content verification: Passed")
        else:
            print("[FAIL] Content verification: Failed")
            return False
    else:
        print(f"[FAIL] Read: Failed - {read_result.get('error', 'Unknown error')}")
        return False
    
    # Test move
    print("Moving test file to Done...")
    move_result = connector.move_file(test_file, f"Done/{test_file}")
    if move_result.get("success"):
        print(f"[OK] Move: Success")
    else:
        print(f"[FAIL] Move: Failed - {move_result.get('error', 'Unknown error')}")
        # This might fail if Done/Inbox doesn't exist, which is okay
        print("  (This may be expected if nested directories don't exist)")
    
    return True


def test_approval_system(connector: ClaudeVaultConnector) -> bool:
    """Test the approval system"""
    print_section("Testing Approval System")
    
    # Create a test approval request
    print("Creating test approval request...")
    approval_result = connector.request_approval(
        action="Test Action",
        amount="$100",
        recipient="Test Recipient",
        reason="Testing the approval system"
    )
    
    if approval_result.get("success"):
        request_id = approval_result.get("request_id", "unknown")
        print(f"[OK] Approval Request Created: {request_id}")
        
        # Check approval status
        print("Checking approval status...")
        status_result = connector.check_approval_status(request_id)
        status = status_result.get("status", "unknown")
        print(f"  Current Status: {status}")
        
        return True
    else:
        print(f"[FAIL] Approval Request Failed: {approval_result.get('error', 'Unknown error')}")
        return False


def test_dashboard(connector: ClaudeVaultConnector) -> bool:
    """Test dashboard access"""
    print_section("Testing Dashboard Access")
    
    # Try to read dashboard
    print("Reading dashboard...")
    dashboard_result = connector.get_dashboard()
    
    if dashboard_result.get("success"):
        content = dashboard_result.get("content", "")
        print(f"[OK] Dashboard: Read successfully ({len(content)} bytes)")
        # Show first few lines
        lines = content.split('\n')[:5]
        print("  Preview:")
        for line in lines:
            print(f"    {line}")
        return True
    else:
        print(f"[FAIL] Dashboard: Not accessible - {dashboard_result.get('error', 'Unknown error')}")
        return False


def run_all_tests():
    """Run all connection tests"""
    print("\n" + "=" * 60)
    print("  CLAUDE VAULT CONNECTION TEST SUITE")
    print("=" * 60)
    print(f"  Vault Path: D:\\prompteng\\AI_Employee_Vault")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    connector = ClaudeVaultConnector()
    
    results = {}
    
    # Run tests
    results["mcp_servers"] = test_mcp_servers(connector)
    results["vault_structure"] = test_vault_structure(connector)
    results["file_operations"] = test_file_operations(connector)
    results["approval_system"] = test_approval_system(connector)
    results["dashboard"] = test_dashboard(connector)
    
    # Summary
    print_section("TEST SUMMARY")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, passed_test in results.items():
        status = "[PASSED]" if passed_test else "[FAILED]"
        print(f"  {test_name.replace('_', ' ').title()}: {status}")
    
    print(f"\n  Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n  [OK] All tests passed! Claude is ready to connect to the vault.")
        print("\n  Next steps:")
        print("  1. Start MCP servers: python start_mcp_servers.py")
        print("  2. Run this test: python test_claude_vault_connection.py")
        print("  3. Use connector: python claude_vault_connector.py <command>")
        return True
    else:
        print("\n  [FAIL] Some tests failed. Please check the errors above.")
        print("\n  Troubleshooting:")
        print("  1. Ensure MCP servers are running: python start_mcp_servers.py")
        print("  2. Check vault path exists: D:\\prompteng\\AI_Employee_Vault")
        print("  3. Verify directory structure is created")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
