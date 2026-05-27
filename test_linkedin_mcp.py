"""
LinkedIn MCP Integration Tests
Tests for LinkedIn MCP server and skill integration
"""

import unittest
import requests
import time
from pathlib import Path


class TestLinkedInMCPIntegration(unittest.TestCase):
    """Integration tests for LinkedIn MCP server"""

    MCP_URL = "http://localhost:8002"
    VAULT_PATH = Path(r"D:\prompteng\AI_Employee_Vault")

    def test_server_running(self):
        """Test if LinkedIn MCP server is running"""
        try:
            response = requests.get(f"{self.MCP_URL}/capabilities", timeout=5)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data.get("name"), "linkedin-mcp")
            print("[OK] LinkedIn MCP Server Running")
        except requests.exceptions.ConnectionError:
            self.fail("LinkedIn MCP Server is not running. Start with: python start_mcp_servers.py")

    def test_skill_registered(self):
        """Test if LinkedIn skill is registered"""
        try:
            from skills.registry import get_skill
            skill = get_skill('linkedin_mcp_action')
            self.assertIsNotNone(skill)
            self.assertEqual(skill.name, 'linkedin_mcp_action')
            print("[OK] LinkedIn MCP Action Skill Registered")
        except Exception as e:
            self.fail(f"LinkedIn skill not registered: {e}")

    def test_capabilities_endpoint(self):
        """Test capabilities endpoint"""
        response = requests.get(f"{self.MCP_URL}/capabilities", timeout=5)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn("name", data)
        self.assertIn("version", data)
        self.assertIn("operations", data)
        
        operations = data.get("operations", [])
        operation_names = [op["name"] for op in operations]
        
        expected_ops = ["create_post", "create_draft", "get_auth_url"]
        for op in expected_ops:
            self.assertIn(op, operation_names, f"Missing operation: {op}")
        
        print("[OK] Capabilities Endpoint Working")

    def test_draft_creation(self):
        """Test draft post creation workflow"""
        draft_data = {
            "text": f"Test draft post - {time.time()}",
            "visibility": "PUBLIC"
        }
        
        response = requests.post(
            f"{self.MCP_URL}/create_draft",
            json=draft_data,
            timeout=10
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertTrue(data.get("success"))
        self.assertIn("filepath", data)
        self.assertIn("filename", data)
        
        # Verify file exists
        filepath = Path(data["filepath"])
        self.assertTrue(filepath.exists(), f"Draft file not created: {filepath}")
        
        # Verify file content
        content = filepath.read_text(encoding='utf-8')
        self.assertIn("type: linkedin_draft", content)
        self.assertIn("status: pending_approval", content)
        self.assertIn(draft_data["text"][:20], content)
        
        print(f"[OK] Draft Creation Working - File: {data['filename']}")
        
        # Clean up: move draft to rejected for cleanup
        rejected_dir = self.VAULT_PATH / "Rejected" / "LinkedIn_Drafts"
        rejected_dir.mkdir(parents=True, exist_ok=True)
        rejected_file = rejected_dir / data["filename"]
        try:
            filepath.rename(rejected_file)
        except Exception:
            pass  # Cleanup is optional

    def test_all_skills_loaded(self):
        """Test that all skills including LinkedIn are loadable"""
        from skills.registry import get_all_skills
        
        skills = get_all_skills()
        skill_names = [s.name for s in skills]
        
        expected_skills = [
            'file_system_watcher',
            'gmail_watcher',
            'filesystem_mcp_action',
            'approval_mcp_action',
            'email_mcp_action',
            'linkedin_mcp_action'
        ]
        
        for skill_name in expected_skills:
            self.assertIn(skill_name, skill_names, f"Missing skill: {skill_name}")
        
        print(f"[OK] All Skills Loaded ({len(skills)} total)")


class TestLinkedInSkill(unittest.TestCase):
    """Unit tests for LinkedIn skill functionality"""

    def setUp(self):
        """Set up test fixtures"""
        from skills.registry import get_skill
        self.skill = get_skill('linkedin_mcp_action')

    def test_skill_metadata(self):
        """Test skill metadata"""
        self.assertEqual(self.skill.name, 'linkedin_mcp_action')
        self.assertEqual(self.skill.version, '1.0.0')
        self.assertTrue(self.skill.enabled)
        print("[OK] Skill Metadata Correct")

    def test_validate_inputs_create_post(self):
        """Test input validation for create_post"""
        # Valid input
        valid, error = self.skill.validate_inputs({
            'action': 'create_post',
            'text': 'Test post'
        })
        self.assertTrue(valid)
        
        # Missing text
        valid, error = self.skill.validate_inputs({
            'action': 'create_post'
        })
        self.assertFalse(valid)
        self.assertIn("text", error)
        
        print("[OK] Input Validation Working")

    def test_validate_inputs_create_draft(self):
        """Test input validation for create_draft"""
        # Valid input
        valid, error = self.skill.validate_inputs({
            'action': 'create_draft',
            'text': 'Test draft'
        })
        self.assertTrue(valid)
        
        # Missing text
        valid, error = self.skill.validate_inputs({
            'action': 'create_draft'
        })
        self.assertFalse(valid)
        
        print("[OK] Draft Validation Working")

    def test_validate_inputs_check_draft(self):
        """Test input validation for check_draft"""
        # Valid input
        valid, error = self.skill.validate_inputs({
            'action': 'check_draft',
            'filename': 'test.md'
        })
        self.assertTrue(valid)
        
        # Missing filename
        valid, error = self.skill.validate_inputs({
            'action': 'check_draft'
        })
        self.assertFalse(valid)
        self.assertIn("filename", error)
        
        print("[OK] Check Draft Validation Working")

    def test_capability_description(self):
        """Test capability description"""
        desc = self.skill.get_capability_description()
        self.assertIn("LinkedIn MCP Action Skill", desc)
        self.assertIn("create_post", desc)
        self.assertIn("create_draft", desc)
        print("[OK] Capability Description Correct")


def run_tests():
    """Run all LinkedIn integration tests"""
    print("=" * 60)
    print("LinkedIn MCP Integration Tests")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add tests
    suite.addTests(loader.loadTestsFromTestCase(TestLinkedInMCPIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestLinkedInSkill))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "=" * 60)
    print(f"Tests: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n[SUCCESS] All LinkedIn integration tests passed!")
    else:
        print("\n[WARNING] Some tests failed. Check LinkedIn MCP setup.")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    run_tests()
