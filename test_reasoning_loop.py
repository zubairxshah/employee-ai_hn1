"""
Claude Reasoning Loop Tests
Tests for reasoning module, Claude integration, and orchestrator reasoning
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime


class TestReasoningModule(unittest.TestCase):
    """Tests for the Claude Reasoning Module"""

    def setUp(self):
        """Set up test fixtures"""
        # Create temporary vault for testing
        self.test_vault = tempfile.mkdtemp()
        self.vault_path = Path(self.test_vault)
        
        # Create vault structure
        (self.vault_path / "Needs_Action").mkdir()
        (self.vault_path / "Plans").mkdir()
        (self.vault_path / "Done").mkdir()
        
        # Import reasoning module
        from reasoning_module import ClaudeReasoningModule
        self.reasoning = ClaudeReasoningModule(str(self.vault_path))
    
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.test_vault, ignore_errors=True)
    
    def test_reasoning_module_initialization(self):
        """Test reasoning module initializes correctly"""
        self.assertEqual(self.reasoning.vault_path, self.vault_path)
        self.assertTrue(self.reasoning.plans_dir.exists())
        print("[OK] Reasoning Module Initialization")
    
    def test_analyze_task(self):
        """Test task analysis"""
        # Create a test task file
        task_file = self.vault_path / "Needs_Action" / "test_task.md"
        task_content = """---
type: email_response
from: client@example.com
subject: Urgent: Project Update
---

# Email from Client

Hi, I need an urgent update on the project status.

## Suggested Action
- Send a response with current project status
- Schedule a follow-up call
"""
        task_file.write_text(task_content)
        
        # Analyze the task
        analysis = self.reasoning.analyze_task(task_file)
        
        self.assertTrue(analysis.get("success"))
        self.assertEqual(analysis.get("task_type"), "email_response")
        self.assertEqual(analysis.get("complexity"), "simple")
        self.assertIn("Suggested Action", analysis.get("content_preview", ""))
        
        print("[OK] Task Analysis")
    
    def test_create_plan(self):
        """Test plan creation"""
        # Create analysis result
        analysis = {
            "success": True,
            "task_name": "test_task",
            "task_type": "email_response",
            "complexity": "simple",
            "requires_approval": False,
            "suggested_actions": [
                "Read email content",
                "Draft response",
                "Send response"
            ],
            "content_preview": "Test email content..."
        }
        
        # Create plan
        result = self.reasoning.create_plan(analysis)
        
        self.assertTrue(result.get("success"))
        self.assertIn("plan_path", result)
        self.assertTrue(Path(result["plan_path"]).exists())
        
        # Verify plan content
        plan_content = Path(result["plan_path"]).read_text()
        self.assertIn("test_task", plan_content)
        self.assertIn("email_response", plan_content)
        self.assertIn("- [ ] Step 1:", plan_content)
        
        print(f"[OK] Plan Creation - {result['plan_filename']}")
    
    def test_update_plan_progress(self):
        """Test progress tracking"""
        # Create a plan first
        analysis = {
            "success": True,
            "task_name": "progress_test",
            "task_type": "general",
            "complexity": "simple",
            "requires_approval": False,
            "suggested_actions": ["Step 1", "Step 2"],
            "content_preview": "Test content"
        }
        
        plan_result = self.reasoning.create_plan(analysis)
        
        # Update progress
        progress = self.reasoning.update_plan_progress(
            "progress_test",
            "Completed step 1",
            {"success": True}
        )
        
        self.assertTrue(progress.get("success"))
        self.assertEqual(progress.get("steps_completed"), 1)
        self.assertEqual(progress.get("progress_percent"), 50.0)
        
        print("[OK] Progress Tracking")
    
    def test_check_completion(self):
        """Test completion detection"""
        # Create a plan with 2 steps
        analysis = {
            "success": True,
            "task_name": "completion_test",
            "task_type": "general",
            "complexity": "simple",
            "requires_approval": False,
            "suggested_actions": ["Step 1", "Step 2"],
            "content_preview": "Test content"
        }
        
        self.reasoning.create_plan(analysis)
        
        # Initially incomplete
        completion = self.reasoning.check_completion("completion_test")
        self.assertFalse(completion.get("complete"))
        
        # Complete both steps
        self.reasoning.update_plan_progress("completion_test", "Step 1", {"success": True})
        self.reasoning.update_plan_progress("completion_test", "Step 2", {"success": True})
        
        # Now should be complete
        completion = self.reasoning.check_completion("completion_test")
        self.assertTrue(completion.get("complete"))
        self.assertEqual(completion.get("reason"), "All steps completed")
        
        print("[OK] Completion Detection")
    
    def test_classify_task(self):
        """Test task classification"""
        # Test email task
        metadata = {"type": "email_response"}
        content = "Please reply to this email"
        task_type = self.reasoning._classify_task(metadata, content)
        self.assertEqual(task_type, "email_response")
        
        # Test financial task
        metadata = {"type": ""}
        content = "Invoice payment required for $500"
        task_type = self.reasoning._classify_task(metadata, content)
        self.assertEqual(task_type, "financial")
        
        # Test LinkedIn task
        content = "Post this update to LinkedIn"
        task_type = self.reasoning._classify_task(metadata, content)
        self.assertEqual(task_type, "social_media")
        
        print("[OK] Task Classification")
    
    def test_check_approval_required(self):
        """Test approval requirement detection"""
        # Test explicit approval flag
        metadata = {"requires_approval": "true"}
        self.assertTrue(self.reasoning._check_approval_required(metadata, "general"))
        
        # Test financial threshold
        metadata = {"amount": "$500"}
        self.assertTrue(self.reasoning._check_approval_required(metadata, "financial"))
        
        # Test below threshold
        metadata = {"amount": "$50"}
        self.assertFalse(self.reasoning._check_approval_required(metadata, "financial"))
        
        print("[OK] Approval Requirement Detection")


class TestClaudeIntegration(unittest.TestCase):
    """Tests for Claude Code Integration"""

    def setUp(self):
        """Set up test fixtures"""
        self.test_vault = tempfile.mkdtemp()
        self.vault_path = Path(self.test_vault)
        
        # Create vault structure
        (self.vault_path / "Needs_Action").mkdir()
        (self.vault_path / "Plans").mkdir()
        
        # Import modules
        from reasoning_module import ClaudeReasoningModule
        from claude_integration import ClaudeCodeIntegration
        
        self.reasoning = ClaudeReasoningModule(str(self.vault_path))
        self.claude = ClaudeCodeIntegration(str(self.vault_path), self.reasoning)
    
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.test_vault, ignore_errors=True)
    
    def test_claude_integration_initialization(self):
        """Test Claude integration initializes correctly"""
        self.assertEqual(self.claude.vault_path, self.vault_path)
        self.assertIsNotNone(self.claude.reasoning_module)
        print("[OK] Claude Integration Initialization")
    
    def test_build_claude_prompt(self):
        """Test prompt building for Claude"""
        task_analysis = {
            "task_name": "test_task",
            "task_type": "email_response",
            "complexity": "simple",
            "requires_approval": False,
            "content_preview": "Test email content",
            "suggested_actions": ["Action 1", "Action 2"]
        }
        
        prompt = self.claude._build_claude_prompt(task_analysis)
        
        self.assertIn("test_task", prompt)
        self.assertIn("email_response", prompt)
        self.assertIn("Action 1", prompt)
        self.assertIn("Action 2", prompt)
        self.assertIn("Company Handbook", prompt)
        
        print("[OK] Claude Prompt Building")
    
    def test_parse_claude_response_json(self):
        """Test parsing Claude's JSON response"""
        response = """
Here's my analysis:

```json
{
    "understanding": "This is a test task",
    "decision": "Execute the suggested actions",
    "steps": [
        {"name": "Step 1", "action": "email_mcp_action"},
        {"name": "Step 2", "action": "linkedin_mcp_action"}
    ],
    "requires_approval": false,
    "risks": ["None identified"]
}
```
"""
        parsed = self.claude._parse_claude_response(response)
        
        self.assertEqual(parsed.get("understanding"), "This is a test task")
        self.assertEqual(len(parsed.get("steps", [])), 2)
        self.assertFalse(parsed.get("requires_approval"))
        
        print("[OK] Claude Response Parsing")
    
    def test_fallback_plan_generation(self):
        """Test fallback plan when Claude is unavailable"""
        task_analysis = {
            "task_name": "fallback_test",
            "task_type": "email_response",
            "requires_approval": True,
            "suggested_actions": [
                "Send email response",
                "Post to LinkedIn",
                "Move file to Done"
            ],
            "content_preview": "Test content"
        }
        
        fallback = self.claude._generate_fallback_plan(task_analysis)
        
        self.assertIn("steps", fallback)
        self.assertEqual(len(fallback.get("steps", [])), 3)
        self.assertTrue(fallback.get("requires_approval"))
        self.assertTrue(fallback.get("fallback_mode"))
        
        print("[OK] Fallback Plan Generation")


class TestReasoningLoop(unittest.TestCase):
    """Integration tests for the complete reasoning loop"""

    def setUp(self):
        """Set up test fixtures"""
        self.test_vault = tempfile.mkdtemp()
        self.vault_path = Path(self.test_vault)
        
        # Create vault structure
        (self.vault_path / "Needs_Action").mkdir()
        (self.vault_path / "Plans").mkdir()
        (self.vault_path / "Done").mkdir()
        
        # Import modules
        from reasoning_module import ClaudeReasoningModule
        from claude_integration import ClaudeCodeIntegration
        
        self.reasoning = ClaudeReasoningModule(str(self.vault_path))
        self.claude = ClaudeCodeIntegration(str(self.vault_path), self.reasoning)
    
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.test_vault, ignore_errors=True)
    
    def test_full_reasoning_loop(self):
        """Test complete reasoning loop without Claude (fallback mode)"""
        # Create a test task file
        task_file = self.vault_path / "Needs_Action" / "loop_test.md"
        task_content = """---
type: email_response
from: test@example.com
---

# Test Task

Please process this task.

## Suggested Action
- Send email response
"""
        task_file.write_text(task_content)
        
        # Mock skill executor
        def mock_executor(skill_name, parameters):
            return {"success": True, "skill": skill_name}
        
        # Run reasoning loop (will use fallback since Claude CLI not available)
        result = self.claude.run_reasoning_loop(task_file, mock_executor)
        
        # Verify loop completed
        self.assertIn("stages", result)
        self.assertIn("analysis", result["stages"])
        self.assertIn("plan_creation", result["stages"])
        self.assertIn("execution", result["stages"])
        
        # Analysis should succeed
        self.assertTrue(result["stages"]["analysis"].get("success"))
        
        # Plan should be created
        self.assertTrue(result["stages"]["plan_creation"].get("success"))
        
        print("[OK] Full Reasoning Loop")


def run_tests():
    """Run all reasoning loop tests"""
    print("=" * 60)
    print("Claude Reasoning Loop Tests")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add tests
    suite.addTests(loader.loadTestsFromTestCase(TestReasoningModule))
    suite.addTests(loader.loadTestsFromTestCase(TestClaudeIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestReasoningLoop))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "=" * 60)
    print(f"Tests: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n[SUCCESS] All reasoning loop tests passed!")
    else:
        print("\n[WARNING] Some tests failed.")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    run_tests()
