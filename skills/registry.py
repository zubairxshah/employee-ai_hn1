"""
Skill Registry
Central registry for discovering and managing Agent Skills
"""

import importlib
import importlib.util
import logging
from pathlib import Path
from typing import Dict, List, Optional, Type
import yaml
import os

from . import AgentSkill


logger = logging.getLogger("skills.registry")


class SkillRegistry:
    """
    Central registry for Agent Skills.
    
    Provides:
    - Skill discovery and registration
    - Skill instantiation with configuration
    - Skill listing and metadata
    - YAML-based configuration loading
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize the skill registry.
        
        Args:
            config_dir: Path to directory containing skill YAML configurations
        """
        self._skills: Dict[str, AgentSkill] = {}
        self._skill_classes: Dict[str, Type[AgentSkill]] = {}
        self._config_dir = Path(config_dir) if config_dir else None
        self._configurations: Dict[str, dict] = {}
        
        # Load configurations if config_dir is provided
        if self._config_dir and self._config_dir.exists():
            self._load_configurations()
    
    def _load_configurations(self):
        """Load skill configurations from YAML files"""
        if not self._config_dir:
            return
        
        for yaml_file in self._config_dir.glob("*.yaml"):
            try:
                with open(yaml_file, 'r') as f:
                    config = yaml.safe_load(f)
                    skill_name = config.get('name', yaml_file.stem)
                    self._configurations[skill_name] = config
                    logger.info(f"Loaded configuration for skill: {skill_name}")
            except Exception as e:
                logger.error(f"Failed to load config {yaml_file}: {e}")
    
    def register(self, skill_class: Type[AgentSkill], name: Optional[str] = None) -> None:
        """
        Register a skill class.
        
        Args:
            skill_class: The AgentSkill subclass to register
            name: Optional custom name (defaults to class name)
        """
        if not issubclass(skill_class, AgentSkill):
            raise TypeError(f"{skill_class.__name__} must be a subclass of AgentSkill")
        
        skill_name = name or skill_class.__name__
        self._skill_classes[skill_name] = skill_class
        logger.info(f"Registered skill: {skill_name}")
    
    def unregister(self, name: str) -> bool:
        """
        Unregister a skill.
        
        Args:
            name: Name of the skill to unregister
        
        Returns:
            True if skill was unregistered, False if not found
        """
        if name in self._skills:
            del self._skills[name]
        if name in self._skill_classes:
            del self._skill_classes[name]
        return True
    
    def get(self, name: str, lazy_init: bool = True) -> Optional[AgentSkill]:
        """
        Get a skill instance by name.
        
        Args:
            name: Name of the skill
            lazy_init: If True, initialize skill on first access
        
        Returns:
            Skill instance or None if not found
        """
        # Return cached instance if available
        if name in self._skills:
            return self._skills[name]
        
        # Load and instantiate if lazy_init is True
        if lazy_init and name in self._skill_classes:
            config = self._configurations.get(name, {})
            return self._instantiate(name, config)
        
        return None
    
    def _instantiate(self, name: str, config: dict) -> Optional[AgentSkill]:
        """
        Instantiate a skill with configuration.
        
        Args:
            name: Skill name
            config: Configuration dictionary
        
        Returns:
            Skill instance or None if instantiation fails
        """
        if name not in self._skill_classes:
            logger.error(f"Skill not registered: {name}")
            return None
        
        try:
            skill_class = self._skill_classes[name]
            skill_config = config.get('config', {})
            
            # Add common config from registry
            skill_config['registry_name'] = name
            
            skill = skill_class(skill_config)
            self._skills[name] = skill
            logger.info(f"Instantiated skill: {name}")
            return skill
            
        except Exception as e:
            logger.error(f"Failed to instantiate skill {name}: {e}")
            return None
    
    def list_skills(self) -> List[str]:
        """
        List all registered skill names.
        
        Returns:
            List of skill names
        """
        return list(self._skill_classes.keys())
    
    def get_metadata(self, name: str) -> Optional[Dict]:
        """
        Get metadata for a skill.
        
        Args:
            name: Skill name
        
        Returns:
            Metadata dictionary or None if not found
        """
        skill = self.get(name)
        if skill:
            return skill.get_metadata()
        return None
    
    def get_all_metadata(self) -> Dict[str, Dict]:
        """
        Get metadata for all registered skills.
        
        Returns:
            Dictionary mapping skill names to metadata
        """
        return {
            name: self.get_metadata(name)
            for name in self.list_skills()
        }
    
    def discover_skills(self, module_path: str, package: str = "skills") -> int:
        """
        Discover and register skills from a module path.
        
        Args:
            module_path: Path to module directory
            package: Base package name
        
        Returns:
            Number of skills discovered
        """
        count = 0
        path = Path(module_path)
        
        if not path.exists():
            logger.warning(f"Module path does not exist: {module_path}")
            return 0
        
        # Find all Python files in the module path
        for py_file in path.rglob("*.py"):
            if py_file.name.startswith("_"):
                continue
            
            # Build module name
            rel_path = py_file.relative_to(path.parent)
            module_name = str(rel_path.with_suffix('')).replace(os.sep, '.')
            
            try:
                # Import the module
                full_module_name = f"{package}.{module_name}"
                module = importlib.import_module(full_module_name)
                
                # Find AgentSkill subclasses
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and 
                        issubclass(attr, AgentSkill) and 
                        attr is not AgentSkill):
                        self.register(attr)
                        count += 1
                        logger.info(f"Discovered skill: {attr_name} in {module_name}")
                        
            except Exception as e:
                logger.debug(f"Could not import {py_file}: {e}")
        
        return count
    
    def execute(self, name: str, context: Dict, parameters: Dict) -> Dict:
        """
        Execute a skill by name.
        
        Args:
            name: Skill name
            context: Execution context
            parameters: Skill parameters
        
        Returns:
            Execution result
        """
        skill = self.get(name)
        if not skill:
            return {
                "success": False,
                "error": f"Skill not found: {name}",
                "available_skills": self.list_skills()
            }
        
        return skill.run(context, parameters)


# Global registry instance
_registry: Optional[SkillRegistry] = None


def get_registry(config_dir: Optional[str] = None) -> SkillRegistry:
    """
    Get the global skill registry instance.
    
    Args:
        config_dir: Optional path to configuration directory
    
    Returns:
        SkillRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = SkillRegistry(config_dir)
    return _registry


def register_skill(skill_class: Type[AgentSkill], name: Optional[str] = None) -> None:
    """
    Register a skill with the global registry.
    
    Args:
        skill_class: AgentSkill subclass
        name: Optional custom name
    """
    get_registry().register(skill_class, name)


def get_skill(name: str) -> Optional[AgentSkill]:
    """
    Get a skill from the global registry.
    
    Args:
        name: Skill name
    
    Returns:
        Skill instance or None
    """
    return get_registry().get(name)


def execute_skill(name: str, context: Dict, parameters: Dict) -> Dict:
    """
    Execute a skill from the global registry.
    
    Args:
        name: Skill name
        context: Execution context
        parameters: Skill parameters
    
    Returns:
        Execution result
    """
    return get_registry().execute(name, context, parameters)
