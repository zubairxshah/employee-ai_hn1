"""
Agent Skill Base Class
All AI skills in the Personal AI Employee system inherit from this class
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pathlib import Path
import logging
from datetime import datetime


class AgentSkill(ABC):
    """
    Abstract base class for all Agent Skills.
    
    Each skill should:
    - Be modular and reusable
    - Have clear input validation
    - Provide capability descriptions
    - Handle errors gracefully
    - Log all actions for audit purposes
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the skill with configuration.
        
        Args:
            config: Dictionary containing skill-specific configuration
        """
        self.config = config or {}
        self.name = self.__class__.__name__
        self.version = "1.0.0"
        self.created_at = datetime.now()
        self.execution_count = 0
        self.last_error: Optional[str] = None
        
        # Set up logging
        self.logger = logging.getLogger(f"skills.{self.name}")
        
        # Initialize skill-specific setup
        self._setup()
    
    @abstractmethod
    def execute(self, context: Dict[str, Any], parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the skill with given context and parameters.
        
        Args:
            context: Current execution context (vault path, user preferences, etc.)
            parameters: Skill-specific parameters
        
        Returns:
            Dictionary containing execution results and any output data
        """
        pass
    
    def validate_inputs(self, parameters: Dict[str, Any]) -> tuple[bool, str]:
        """
        Validate input parameters before execution.
        
        Args:
            parameters: Parameters to validate
        
        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if parameters are valid
            - error_message: Empty string if valid, error description otherwise
        """
        # Default implementation - always valid
        # Override in subclasses for specific validation
        return True, ""
    
    def get_capability_description(self) -> str:
        """
        Return a description of what the skill does.
        
        Returns:
            Human-readable description of the skill's capabilities
        """
        return f"Agent Skill: {self.name} (v{self.version})"
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Return metadata about the skill.
        
        Returns:
            Dictionary containing skill metadata
        """
        return {
            "name": self.name,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "execution_count": self.execution_count,
            "last_error": self.last_error,
            "config_keys": list(self.config.keys()) if self.config else []
        }
    
    def _setup(self):
        """
        Setup hook for skill-specific initialization.
        Override in subclasses if needed.
        """
        pass
    
    def _pre_execute(self, context: Dict[str, Any], parameters: Dict[str, Any]) -> bool:
        """
        Pre-execution hook. Runs before execute().
        
        Args:
            context: Execution context
            parameters: Skill parameters
        
        Returns:
            True to proceed with execution, False to abort
        """
        # Validate inputs
        is_valid, error_msg = self.validate_inputs(parameters)
        if not is_valid:
            self.last_error = error_msg
            self.logger.error(f"Input validation failed: {error_msg}")
            return False
        
        self.logger.info(f"Executing {self.name} with parameters: {parameters}")
        return True
    
    def _post_execute(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Post-execution hook. Runs after execute().
        
        Args:
            result: Execution result
        
        Returns:
            Modified result (or same result if no modification needed)
        """
        self.execution_count += 1
        self.last_error = None
        self.logger.info(f"{self.name} execution completed successfully")
        return result
    
    def _handle_error(self, error: Exception) -> Dict[str, Any]:
        """
        Error handler for skill execution.
        
        Args:
            error: The exception that was raised
        
        Returns:
            Error result dictionary
        """
        self.last_error = str(error)
        self.logger.error(f"{self.name} execution failed: {error}")
        
        return {
            "success": False,
            "error": str(error),
            "error_type": type(error).__name__,
            "skill": self.name
        }
    
    def run(self, context: Dict[str, Any], parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point for skill execution.
        Handles pre/post hooks and error handling.
        
        Args:
            context: Execution context
            parameters: Skill parameters
        
        Returns:
            Execution result dictionary
        """
        try:
            # Pre-execution checks
            if not self._pre_execute(context, parameters):
                return {
                    "success": False,
                    "error": "Input validation failed",
                    "skill": self.name
                }
            
            # Execute the skill
            result = self.execute(context, parameters)
            
            # Post-execution processing
            result = self._post_execute(result)
            
            return result
            
        except Exception as e:
            return self._handle_error(e)
