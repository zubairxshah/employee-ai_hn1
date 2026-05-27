"""
Claude Reasoning Module
Implements the reasoning loop for task analysis, planning, and progress tracking
"""

import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional


class ClaudeReasoningModule:
    """
    Claude Reasoning Module for task analysis and planning.
    
    This module:
    - Analyzes tasks from Needs_Action folder
    - Creates structured Plan.md files
    - Tracks progress
    - Detects completion
    """

    def __init__(self, vault_path: str):
        """
        Initialize the reasoning module.
        
        Args:
            vault_path: Path to the Obsidian vault
        """
        self.vault_path = Path(vault_path)
        self.plans_dir = self.vault_path / "Plans"
        self.needs_action_dir = self.vault_path / "Needs_Action"
        self.done_dir = self.vault_path / "Done"
        
        # Ensure directories exist
        self.plans_dir.mkdir(parents=True, exist_ok=True)
        
        # Task state tracking
        self.active_plans: Dict[str, Dict] = {}
        
    def analyze_task(self, task_file: Path) -> Dict[str, Any]:
        """
        Analyze a task file and extract key information.
        
        Args:
            task_file: Path to the task file
            
        Returns:
            Dictionary with task analysis
        """
        if not task_file.exists():
            return {
                "success": False,
                "error": f"Task file not found: {task_file}"
            }
        
        content = task_file.read_text(encoding='utf-8')
        
        # Extract metadata from frontmatter
        metadata = self._parse_frontmatter(content)
        
        # Extract main content
        main_content = self._extract_main_content(content)
        
        # Analyze task type and complexity
        task_type = self._classify_task(metadata, main_content)
        complexity = self._assess_complexity(main_content)
        requires_approval = self._check_approval_required(metadata, task_type)
        
        # Extract suggested actions
        suggested_actions = self._extract_suggested_actions(main_content)
        
        analysis = {
            "success": True,
            "task_file": str(task_file),
            "task_name": task_file.stem,
            "metadata": metadata,
            "task_type": task_type,
            "complexity": complexity,
            "requires_approval": requires_approval,
            "suggested_actions": suggested_actions,
            "content_preview": main_content[:200] + "..." if len(main_content) > 200 else main_content,
            "analyzed_at": datetime.now().isoformat()
        }
        
        return analysis
    
    def create_plan(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a Plan.md file based on task analysis.
        
        Args:
            analysis: Task analysis dictionary
            
        Returns:
            Dictionary with plan creation result
        """
        if not analysis.get("success"):
            return {
                "success": False,
                "error": "Invalid analysis provided"
            }
        
        task_name = analysis.get("task_name", "unknown_task")
        plan_filename = f"PLAN_{task_name}_{int(time.time())}.md"
        plan_path = self.plans_dir / plan_filename
        
        # Build plan content
        plan_content = self._build_plan_content(analysis)
        
        # Write plan file
        plan_path.write_text(plan_content, encoding='utf-8')
        
        # Track active plan
        self.active_plans[task_name] = {
            "plan_path": str(plan_path),
            "status": "active",
            "created_at": datetime.now().isoformat(),
            "steps_total": len(analysis.get("suggested_actions", [])),
            "steps_completed": 0
        }
        
        return {
            "success": True,
            "plan_path": str(plan_path),
            "plan_filename": plan_filename,
            "task_name": task_name,
            "message": f"Plan created for task: {task_name}"
        }
    
    def update_plan_progress(self, task_name: str, step_completed: str, 
                             step_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update plan progress after completing a step.
        
        Args:
            task_name: Name of the task
            step_completed: Description of the completed step
            step_result: Result of the step execution
            
        Returns:
            Dictionary with updated progress
        """
        if task_name not in self.active_plans:
            return {
                "success": False,
                "error": f"No active plan found for task: {task_name}"
            }
        
        plan = self.active_plans[task_name]
        plan["steps_completed"] += 1
        plan["last_updated"] = datetime.now().isoformat()
        
        # Append progress to plan file
        plan_path = Path(plan["plan_path"])
        if plan_path.exists():
            self._append_progress_to_plan(plan_path, step_completed, step_result)
        
        return {
            "success": True,
            "task_name": task_name,
            "steps_completed": plan["steps_completed"],
            "steps_total": plan["steps_total"],
            "progress_percent": (plan["steps_completed"] / plan["steps_total"] * 100) if plan["steps_total"] > 0 else 0
        }
    
    def check_completion(self, task_name: str) -> Dict[str, Any]:
        """
        Check if a task is complete.
        
        Args:
            task_name: Name of the task
            
        Returns:
            Dictionary with completion status
        """
        if task_name not in self.active_plans:
            return {
                "success": False,
                "error": f"No active plan found for task: {task_name}",
                "complete": False
            }
        
        plan = self.active_plans[task_name]
        
        # Check if all steps are completed
        is_complete = plan["steps_completed"] >= plan["steps_total"]
        
        # Check if task file was moved to Done
        task_moved = self._check_task_moved_to_done(task_name)
        
        completion_status = {
            "success": True,
            "task_name": task_name,
            "complete": is_complete or task_moved,
            "steps_completed": plan["steps_completed"],
            "steps_total": plan["steps_total"],
            "task_moved_to_done": task_moved,
            "reason": "All steps completed" if is_complete else "Task moved to Done folder" if task_moved else "Task in progress"
        }
        
        if completion_status["complete"]:
            plan["status"] = "completed"
            plan["completed_at"] = datetime.now().isoformat()
        
        return completion_status
    
    def get_active_plans(self) -> List[Dict[str, Any]]:
        """
        Get all active plans.
        
        Returns:
            List of active plan dictionaries
        """
        return [
            {
                "task_name": name,
                **info
            }
            for name, info in self.active_plans.items()
            if info["status"] == "active"
        ]
    
    def _parse_frontmatter(self, content: str) -> Dict[str, Any]:
        """Parse YAML frontmatter from content"""
        metadata = {}
        lines = content.split('\n')
        in_frontmatter = False
        
        for line in lines:
            if line.strip() == '---':
                if not in_frontmatter:
                    in_frontmatter = True
                else:
                    break
                continue
            
            if in_frontmatter and ':' in line:
                key, value = line.split(':', 1)
                metadata[key.strip()] = value.strip()
        
        return metadata
    
    def _extract_main_content(self, content: str) -> str:
        """Extract main content after frontmatter"""
        lines = content.split('\n')
        in_frontmatter = False
        main_lines = []
        frontmatter_ended = False
        
        for line in lines:
            if line.strip() == '---':
                if not in_frontmatter:
                    in_frontmatter = True
                else:
                    frontmatter_ended = True
                continue
            
            if frontmatter_ended:
                main_lines.append(line)
        
        return '\n'.join(main_lines).strip()
    
    def _classify_task(self, metadata: Dict, content: str) -> str:
        """Classify task type based on metadata and content"""
        task_type = metadata.get('type', '').lower()
        
        if task_type:
            return task_type
        
        content_lower = content.lower()
        
        if 'email' in content_lower:
            return 'email_response'
        elif 'invoice' in content_lower or 'payment' in content_lower:
            return 'financial'
        elif 'linkedin' in content_lower or 'post' in content_lower:
            return 'social_media'
        elif 'file' in content_lower or 'document' in content_lower:
            return 'file_processing'
        elif 'whatsapp' in content_lower:
            return 'whatsapp_response'
        else:
            return 'general'
    
    def _assess_complexity(self, content: str) -> str:
        """Assess task complexity based on content"""
        word_count = len(content.split())
        
        if word_count < 100:
            return 'simple'
        elif word_count < 500:
            return 'medium'
        else:
            return 'complex'
    
    def _check_approval_required(self, metadata: Dict, task_type: str) -> bool:
        """Check if task requires human approval"""
        # Check metadata for approval flag
        if metadata.get('requires_approval', '').lower() == 'true':
            return True
        
        # Financial tasks over threshold require approval
        if task_type == 'financial':
            amount = metadata.get('amount', '0')
            try:
                if float(amount.replace('$', '').replace(',', '')) > 100:
                    return True
            except (ValueError, AttributeError):
                pass
        
        return False
    
    def _extract_suggested_actions(self, content: str) -> List[str]:
        """Extract suggested actions from content"""
        actions = []
        lines = content.split('\n')
        
        in_actions_section = False
        for line in lines:
            line_lower = line.lower().strip()
            
            if 'suggested action' in line_lower or 'next steps' in line_lower:
                in_actions_section = True
                continue
            
            if in_actions_section:
                if line.startswith('-') or line.startswith('*') or line.startswith('1.'):
                    action = line.lstrip('-*1234567890. ').strip()
                    if action:
                        actions.append(action)
                elif line.strip() and not line.startswith(' '):
                    # End of actions section
                    break
        
        # If no structured actions found, create default based on task type
        if not actions:
            actions = self._generate_default_actions(content)
        
        return actions
    
    def _generate_default_actions(self, content: str) -> List[str]:
        """Generate default actions based on content"""
        actions = []
        
        if 'email' in content.lower():
            actions.extend([
                "Read and analyze email content",
                "Draft appropriate response",
                "Send response or create draft for approval"
            ])
        elif 'linkedin' in content.lower():
            actions.extend([
                "Review post content",
                "Create draft post for approval",
                "Publish approved post"
            ])
        elif 'file' in content.lower():
            actions.extend([
                "Analyze file content",
                "Process according to type",
                "Move to appropriate folder"
            ])
        else:
            actions.extend([
                "Analyze task requirements",
                "Execute required actions",
                "Mark task as complete"
            ])
        
        return actions
    
    def _build_plan_content(self, analysis: Dict[str, Any]) -> str:
        """Build the Plan.md file content"""
        task_name = analysis.get("task_name", "Unknown")
        task_type = analysis.get("task_type", "general")
        complexity = analysis.get("complexity", "unknown")
        requires_approval = analysis.get("requires_approval", False)
        suggested_actions = analysis.get("suggested_actions", [])
        content_preview = analysis.get("content_preview", "")
        
        steps = []
        for i, action in enumerate(suggested_actions, 1):
            steps.append(f"- [ ] Step {i}: {action}")
        
        steps_content = '\n'.join(steps) if steps else "- [ ] No specific steps defined"
        
        plan_content = f"""---
type: plan
task_name: {task_name}
task_type: {task_type}
complexity: {complexity}
requires_approval: {str(requires_approval).lower()}
status: active
created: {datetime.now().isoformat()}
---

# Plan: {task_name}

## Task Analysis

| Property | Value |
|----------|-------|
| Type | {task_type} |
| Complexity | {complexity} |
| Requires Approval | {"Yes" if requires_approval else "No"} |
| Created | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |

## Content Preview

{content_preview}

## Action Steps

{steps_content}

## Progress

- Steps Completed: 0 / {len(suggested_actions)}
- Status: In Progress

## Notes

{self._generate_reasoning_notes(analysis)}

---
*This plan was automatically generated by the Claude Reasoning Module*
"""
        
        return plan_content
    
    def _generate_reasoning_notes(self, analysis: Dict[str, Any]) -> str:
        """Generate reasoning notes based on analysis"""
        notes = []
        
        task_type = analysis.get("task_type", "general")
        
        if task_type == 'email_response':
            notes.append("- This is an email response task")
            notes.append("- Check Company Handbook for communication standards")
            notes.append("- Ensure professional tone in response")
        
        elif task_type == 'financial':
            notes.append("- This is a financial task")
            notes.append("- Check payment amount against approval thresholds")
            notes.append("- Log all actions for audit trail")
        
        elif task_type == 'social_media':
            notes.append("- This is a social media task")
            notes.append("- Ensure content aligns with brand guidelines")
            notes.append("- Consider using draft workflow for approval")
        
        elif analysis.get("requires_approval"):
            notes.append("- This task requires human approval before proceeding")
            notes.append("- Create draft and move to Pending_Approval folder")
        
        if not notes:
            notes.append("- Standard task processing applies")
            notes.append("- Follow Company Handbook guidelines")
        
        return '\n'.join(notes)
    
    def _append_progress_to_plan(self, plan_path: Path, step_completed: str, 
                                  step_result: Dict[str, Any]) -> None:
        """Append progress update to plan file"""
        content = plan_path.read_text(encoding='utf-8')
        
        # Find the Progress section and update it
        progress_update = f"""
### Progress Update - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- Completed: {step_completed}
- Result: {"Success" if step_result.get('success') else 'Failed'}
"""
        
        # Append to content
        new_content = content + "\n" + progress_update
        
        plan_path.write_text(new_content, encoding='utf-utf-8')
    
    def _check_task_moved_to_done(self, task_name: str) -> bool:
        """Check if the original task file was moved to Done folder"""
        # Look for files in Done folder that match the task name
        if not self.done_dir.exists():
            return False
        
        for done_file in self.done_dir.glob(f"*{task_name}*"):
            return True
        
        return False


def get_reasoning_module(vault_path: str) -> ClaudeReasoningModule:
    """
    Factory function to get a reasoning module instance.
    
    Args:
        vault_path: Path to the Obsidian vault
        
    Returns:
        ClaudeReasoningModule instance
    """
    return ClaudeReasoningModule(vault_path)
