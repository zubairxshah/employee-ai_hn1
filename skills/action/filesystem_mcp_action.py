"""
Filesystem MCP Action Skill
Provides file operations via the Filesystem MCP server
"""

import requests
from pathlib import Path
from typing import Any, Dict

from .. import AgentSkill


class FilesystemMCPActionSkill(AgentSkill):
    """
    Skill for performing file operations via the Filesystem MCP server.
    
    Capabilities:
    - Read files from the vault
    - Write files to the vault
    - Move files within the vault
    - List directory contents
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        config = config or {}
        config.setdefault('mcp_url', 'http://localhost:8000')
        config.setdefault('timeout', 30)
        super().__init__(config)
        
        self.mcp_url = self.config.get('mcp_url', 'http://localhost:8000')
        self.timeout = self.config.get('timeout', 30)
    
    def validate_inputs(self, parameters: Dict[str, Any]) -> tuple:
        """Validate input parameters"""
        action = parameters.get('action')
        if not action:
            return False, "Missing required parameter: action"
        
        valid_actions = ['read', 'write', 'move', 'list']
        if action not in valid_actions:
            return False, f"Invalid action. Must be one of: {valid_actions}"
        
        if action in ['read', 'write', 'list'] and 'path' not in parameters:
            return False, f"Missing required parameter for {action}: path"
        
        if action == 'move':
            if 'source' not in parameters:
                return False, "Missing required parameter for move: source"
            if 'destination' not in parameters:
                return False, "Missing required parameter for move: destination"
        
        if action == 'write' and 'content' not in parameters:
            return False, "Missing required parameter for write: content"
        
        return True, ""
    
    def get_capability_description(self) -> str:
        """Return skill description"""
        return (
            f"Filesystem MCP Action Skill (v{self.version}): "
            f"Performs file operations via MCP server at {self.mcp_url}. "
            f"Actions: read, write, move, list"
        )
    
    def _call_mcp(self, endpoint: str, data: Dict) -> Dict:
        """Make a request to the MCP server"""
        url = f"{self.mcp_url}/{endpoint}"
        try:
            response = requests.post(url, json=data, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"MCP request failed: {str(e)}"
            }
    
    def _read_file(self, path: str) -> Dict:
        """Read a file via MCP"""
        result = self._call_mcp('read_file', {"path": path})
        if result.get("success"):
            return {
                "success": True,
                "action": "read",
                "path": path,
                "content": result.get("content", ""),
                "content_length": len(result.get("content", ""))
            }
        return result
    
    def _write_file(self, path: str, content: str) -> Dict:
        """Write a file via MCP"""
        result = self._call_mcp('write_file', {"path": path, "content": content})
        if result.get("success"):
            return {
                "success": True,
                "action": "write",
                "path": path,
                "bytes_written": len(content)
            }
        return result
    
    def _move_file(self, source: str, destination: str) -> Dict:
        """Move a file via MCP"""
        result = self._call_mcp('move_file', {"source": source, "destination": destination})
        if result.get("success"):
            return {
                "success": True,
                "action": "move",
                "source": source,
                "destination": destination
            }
        return result
    
    def _list_files(self, path: str) -> Dict:
        """List files in a directory via MCP"""
        result = self._call_mcp('list_files', {"path": path})
        if result.get("success"):
            return {
                "success": True,
                "action": "list",
                "path": path,
                "files": result.get("files", []),
                "file_count": len(result.get("files", []))
            }
        return result
    
    def execute(self, context: Dict[str, Any], parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the filesystem MCP action skill.
        
        Parameters:
        - action: One of 'read', 'write', 'move', 'list'
        - path: File/directory path (for read, write, list)
        - content: Content to write (for write action)
        - source: Source path (for move action)
        - destination: Destination path (for move action)
        
        Returns:
        - Dictionary with operation results
        """
        action = parameters.get('action')
        
        if action == 'read':
            return self._read_file(parameters['path'])
        
        elif action == 'write':
            return self._write_file(parameters['path'], parameters['content'])
        
        elif action == 'move':
            return self._move_file(parameters['source'], parameters['destination'])
        
        elif action == 'list':
            return self._list_files(parameters['path'])
        
        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}"
            }


# Auto-register the skill when module is imported
def _register():
    from ..registry import register_skill
    register_skill(FilesystemMCPActionSkill, "filesystem_mcp_action")

_register()
