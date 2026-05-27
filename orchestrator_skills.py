"""
Skills-Based Orchestrator for AI Personal Employee
Uses the Agent Skills framework to manage all operations
Includes Claude Reasoning Loop for autonomous task completion
"""

import time
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from skills import AgentSkill
from skills.registry import SkillRegistry, get_registry, execute_skill
from reasoning_module import ClaudeReasoningModule, get_reasoning_module
from claude_integration import ClaudeCodeIntegration, get_claude_integration


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("orchestrator")


class SkillsOrchestrator:
    """
    Orchestrator that uses Agent Skills for all operations.
    
    This replaces the previous orchestrator with a skills-based approach
    that follows the Agent Skills framework defined in AGENT_SKILLS.md.
    """
    
    def __init__(self, vault_path: str, config_dir: Optional[str] = None):
        """
        Initialize the skills orchestrator.

        Args:
            vault_path: Path to the Obsidian vault
            config_dir: Path to skill configuration directory
        """
        self.vault_path = Path(vault_path)
        self.config_dir = config_dir

        # Initialize skill registry
        self.registry = get_registry(config_dir)

        # Discover and register skills
        self._discover_skills()

        # Initialize reasoning module
        self.reasoning_module = get_reasoning_module(str(vault_path))
        
        # Initialize Claude Code integration
        self.claude_integration = get_claude_integration(str(vault_path), self.reasoning_module)

        # Active watchers
        self.active_watchers: List[str] = []

        # Execution state
        self.running = False
        
        # Directory references
        self.needs_action_dir = self.vault_path / "Needs_Action"
        self.plans_dir = self.vault_path / "Plans"

        logger.info(f"Skills Orchestrator initialized with vault: {vault_path}")
        logger.info(f"Reasoning module enabled: {self.reasoning_module is not None}")
        logger.info(f"Claude integration enabled: {self.claude_integration is not None}")
    
    def _discover_skills(self):
        """Discover and register all available skills"""
        skills_dir = Path(__file__).parent / 'skills'
        
        # Discover perception skills
        perception_dir = skills_dir / 'perception'
        if perception_dir.exists():
            count = self.registry.discover_skills(str(perception_dir), 'skills.perception')
            logger.info(f"Discovered {count} perception skills")
        
        # Discover action skills
        action_dir = skills_dir / 'action'
        if action_dir.exists():
            count = self.registry.discover_skills(str(action_dir), 'skills.action')
            logger.info(f"Discovered {count} action skills")
        
        # Discover analysis skills
        analysis_dir = skills_dir / 'analysis'
        if analysis_dir.exists():
            count = self.registry.discover_skills(str(analysis_dir), 'skills.analysis')
            logger.info(f"Discovered {count} analysis skills")
    
    def list_available_skills(self) -> Dict[str, List[str]]:
        """
        List all available skills by category.
        
        Returns:
            Dictionary with skill categories and their skill names
        """
        all_skills = self.registry.list_skills()
        
        # Categorize skills by module
        categories = {
            'perception': [],
            'action': [],
            'analysis': [],
            'core': []
        }
        
        for skill_name in all_skills:
            if 'watcher' in skill_name.lower():
                categories['perception'].append(skill_name)
            elif 'action' in skill_name.lower() or 'mcp' in skill_name.lower():
                categories['action'].append(skill_name)
            elif 'analysis' in skill_name.lower() or 'analyzer' in skill_name.lower():
                categories['analysis'].append(skill_name)
            else:
                categories['core'].append(skill_name)
        
        return categories
    
    def get_skill_metadata(self, skill_name: str) -> Optional[Dict]:
        """
        Get metadata for a specific skill.
        
        Args:
            skill_name: Name of the skill
        
        Returns:
            Skill metadata dictionary or None
        """
        return self.registry.get_metadata(skill_name)
    
    def execute_skill(self, skill_name: str, parameters: Dict[str, Any]) -> Dict:
        """
        Execute a skill with the given parameters.
        
        Args:
            skill_name: Name of the skill to execute
            parameters: Skill parameters
        
        Returns:
            Execution result
        """
        context = {
            'vault_path': str(self.vault_path),
            'orchestrator': 'skills_orchestrator',
            'timestamp': time.time()
        }
        
        logger.info(f"Executing skill: {skill_name}")
        result = self.registry.execute(skill_name, context, parameters)
        
        if result.get('success'):
            logger.info(f"Skill {skill_name} executed successfully")
        else:
            logger.error(f"Skill {skill_name} failed: {result.get('error')}")
        
        return result
    
    def start_watcher(self, watcher_name: str, parameters: Dict[str, Any]) -> bool:
        """
        Start a watcher skill.
        
        Args:
            watcher_name: Name of the watcher skill
            parameters: Watcher parameters
        
        Returns:
            True if watcher started successfully
        """
        if watcher_name in self.active_watchers:
            logger.warning(f"Watcher {watcher_name} is already active")
            return False
        
        # Validate watcher exists
        skill = self.registry.get(watcher_name)
        if not skill:
            logger.error(f"Watcher skill not found: {watcher_name}")
            return False
        
        # Add vault path to parameters if not present
        if 'vault_path' not in parameters:
            parameters['vault_path'] = str(self.vault_path)
        
        # For now, we'll do a single scan. In a full implementation,
        # this would start a background thread for continuous monitoring.
        parameters['scan'] = True
        
        result = self.execute_skill(watcher_name, parameters)
        
        if result.get('success'):
            self.active_watchers.append(watcher_name)
            logger.info(f"Watcher {watcher_name} started")
            return True
        else:
            logger.error(f"Failed to start watcher {watcher_name}: {result.get('error')}")
            return False
    
    def stop_watcher(self, watcher_name: str) -> bool:
        """
        Stop a watcher skill.
        
        Args:
            watcher_name: Name of the watcher to stop
        
        Returns:
            True if watcher was stopped
        """
        if watcher_name not in self.active_watchers:
            logger.warning(f"Watcher {watcher_name} is not active")
            return False
        
        self.active_watchers.remove(watcher_name)
        logger.info(f"Watcher {watcher_name} stopped")
        return True
    
    def run_cycle(self) -> Dict[str, Any]:
        """
        Run one complete cycle of all active watchers.
        
        Returns:
            Dictionary with cycle results
        """
        results = {
            'timestamp': time.time(),
            'watchers_executed': [],
            'total_processed': 0,
            'errors': []
        }
        
        for watcher_name in self.active_watchers:
            try:
                # Get watcher config
                skill = self.registry.get(watcher_name)
                if not skill:
                    continue
                
                # Execute the watcher
                parameters = {
                    'vault_path': str(self.vault_path),
                    'scan': True
                }
                
                # Add watcher-specific config
                if watcher_name == 'file_system_watcher':
                    parameters['drop_folder'] = r"D:\prompteng\AI_Employee_Drop"
                elif watcher_name == 'gmail_watcher':
                    parameters['credentials_path'] = skill.config.get('credentials_path')
                
                result = self.execute_skill(watcher_name, parameters)
                
                if result.get('success'):
                    processed = result.get('emails_processed', result.get('files_processed', 0))
                    results['watchers_executed'].append({
                        'name': watcher_name,
                        'processed': processed
                    })
                    results['total_processed'] += processed
                else:
                    results['errors'].append({
                        'watcher': watcher_name,
                        'error': result.get('error')
                    })
                    
            except Exception as e:
                logger.error(f"Error in watcher {watcher_name}: {e}")
                results['errors'].append({
                    'watcher': watcher_name,
                    'error': str(e)
                })
        
        return results

    def process_task_with_reasoning(self, task_file: Path) -> Dict[str, Any]:
        """
        Process a task file using the Claude reasoning loop.
        
        Args:
            task_file: Path to the task file
            
        Returns:
            Processing results with reasoning
        """
        logger.info(f"Processing task with reasoning: {task_file.name}")
        
        # Define skill executor function
        def skill_executor(skill_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
            """Execute a skill with given parameters"""
            try:
                skill = self.registry.get(skill_name)
                if not skill:
                    return {"success": False, "error": f"Skill not found: {skill_name}"}
                
                context = {
                    'vault_path': str(self.vault_path),
                    'orchestrator': 'skills_orchestrator',
                    'timestamp': time.time()
                }
                
                return self.registry.execute(skill_name, context, parameters)
                
            except Exception as e:
                logger.error(f"Skill execution error: {e}")
                return {"success": False, "error": str(e)}
        
        # Run the reasoning loop
        result = self.claude_integration.run_reasoning_loop(task_file, skill_executor)
        
        if result.get("success"):
            logger.info(f"Task completed: {task_file.name}")
        else:
            logger.warning(f"Task incomplete: {task_file.name} - {result.get('error', 'Unknown error')}")
        
        return result
    
    def scan_needs_action(self) -> List[Path]:
        """
        Scan Needs_Action folder for unprocessed tasks.
        
        Returns:
            List of task file paths
        """
        task_files = []
        
        if not self.needs_action_dir.exists():
            return task_files
        
        # Look for markdown files
        for md_file in self.needs_action_dir.glob("*.md"):
            # Skip Plan files
            if md_file.name.startswith("PLAN_"):
                continue
            
            task_files.append(md_file)
        
        return task_files
    
    def run_reasoning_cycle(self) -> Dict[str, Any]:
        """
        Run one reasoning cycle - process tasks with Claude reasoning.
        
        Returns:
            Dictionary with cycle results
        """
        results = {
            'timestamp': time.time(),
            'tasks_processed': 0,
            'tasks_completed': 0,
            'tasks_in_progress': 0,
            'errors': []
        }
        
        # Scan for tasks
        task_files = self.scan_needs_action()
        
        if not task_files:
            logger.info("No tasks found in Needs_Action folder")
            return results
        
        logger.info(f"Found {len(task_files)} task(s) to process")
        
        for task_file in task_files:
            try:
                # Process task with reasoning
                result = self.process_task_with_reasoning(task_file)
                
                results['tasks_processed'] += 1
                
                if result.get('success'):
                    results['tasks_completed'] += 1
                else:
                    results['tasks_in_progress'] += 1
                    
            except Exception as e:
                logger.error(f"Error processing task {task_file.name}: {e}")
                results['errors'].append({
                    'task_file': str(task_file),
                    'error': str(e)
                })
        
        return results

    def run(self, cycle_interval: int = 60, enable_reasoning: bool = True):
        """
        Run the orchestrator in a continuous loop.

        Args:
            cycle_interval: Seconds between cycles
            enable_reasoning: Whether to enable Claude reasoning loop
        """
        logger.info("Starting Skills Orchestrator...")
        logger.info(f"Reasoning loop enabled: {enable_reasoning}")
        self.running = True

        try:
            while self.running:
                # Run watcher cycle
                watcher_results = self.run_cycle()
                
                # Run reasoning cycle if enabled
                if enable_reasoning:
                    reasoning_results = self.run_reasoning_cycle()
                    
                    logger.info(
                        f"Reasoning cycle: {reasoning_results['tasks_processed']} tasks, "
                        f"{reasoning_results['tasks_completed']} completed, "
                        f"{reasoning_results['tasks_in_progress']} in progress"
                    )
                    
                    if reasoning_results['errors']:
                        for error in reasoning_results['errors']:
                            logger.error(f"Task error: {error['task_file']} - {error['error']}")

                logger.info(
                    f"Cycle completed: {len(watcher_results['watchers_executed'])} watchers, "
                    f"{watcher_results['total_processed']} items processed"
                )

                if watcher_results['errors']:
                    for error in watcher_results['errors']:
                        logger.error(f"Error in {error['watcher']}: {error['error']}")

                time.sleep(cycle_interval)

        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
            self.running = False
        except Exception as e:
            logger.error(f"Orchestrator error: {e}")
            self.running = False

        logger.info("Skills Orchestrator stopped")


def main():
    """Main entry point for the skills orchestrator"""
    vault_path = r"D:\prompteng\AI_Employee_Vault"
    config_dir = str(Path(__file__).parent / 'skills' / 'config')

    orchestrator = SkillsOrchestrator(vault_path, config_dir)

    # List available skills
    print("\n" + "=" * 60)
    print("Available Skills")
    print("=" * 60)

    categories = orchestrator.list_available_skills()
    for category, skills in categories.items():
        if skills:
            print(f"\n{category.upper()}:")
            for skill in skills:
                metadata = orchestrator.get_skill_metadata(skill)
                if metadata:
                    print(f"  - {skill} (v{metadata.get('version', 'unknown')})")

    print("\n" + "=" * 60)
    print("Claude Reasoning Loop")
    print("=" * 60)
    print("The orchestrator now includes Claude reasoning for:")
    print("- Task analysis and breakdown")
    print("- Plan.md generation")
    print("- Progress tracking")
    print("- Completion detection")
    print("=" * 60)

    # Start watchers based on configuration
    # For demo, we'll start the file system watcher
    file_watcher_started = orchestrator.start_watcher(
        'file_system_watcher',
        {'drop_folder': r"D:\prompteng\AI_Employee_Drop"}
    )

    if file_watcher_started:
        print("File System Watcher started")
    else:
        print("Failed to start File System Watcher")

    # Run the orchestrator
    print("\nRunning orchestrator with reasoning loop (Ctrl+C to stop)...")
    orchestrator.run(cycle_interval=30, enable_reasoning=True)


if __name__ == "__main__":
    main()
