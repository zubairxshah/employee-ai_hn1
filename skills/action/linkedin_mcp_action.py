"""
LinkedIn MCP Action Skill
Provides LinkedIn posting capabilities via the LinkedIn MCP server
"""

import os
import requests
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

from .. import AgentSkill


class LinkedInMCPActionSkill(AgentSkill):
    """
    Skill for creating LinkedIn posts via the LinkedIn MCP server.

    Capabilities:
    - Create posts on LinkedIn
    - Create draft posts for approval
    - Check draft approval status
    - Execute approved drafts
    - OAuth authentication management
    """

    def __init__(self, config: Dict[str, Any] = None):
        config = config or {}
        config.setdefault('mcp_url', 'http://localhost:8002')
        config.setdefault('timeout', 30)
        super().__init__(config)

        self.mcp_url = self.config.get('mcp_url', 'http://localhost:8002')
        self.timeout = self.config.get('timeout', 30)

    def validate_inputs(self, parameters: Dict[str, Any]) -> tuple:
        """Validate input parameters"""
        action = parameters.get('action')
        if not action:
            return False, "Missing required parameter: action"

        valid_actions = ['create_post', 'create_draft', 'check_draft', 'execute_draft', 'get_auth_url', 'exchange_token', 'capabilities']
        if action not in valid_actions:
            return False, f"Invalid action. Must be one of: {valid_actions}"

        if action == 'create_post':
            required = ['text']
            for param in required:
                if param not in parameters:
                    return False, f"create_post action requires: {', '.join(required)}"

        if action == 'create_draft':
            required = ['text']
            for param in required:
                if param not in parameters:
                    return False, f"create_draft action requires: {', '.join(required)}"

        if action == 'check_draft' and 'filename' not in parameters:
            return False, "check_draft action requires: filename"

        if action == 'execute_draft' and 'filename' not in parameters:
            return False, "execute_draft action requires: filename"

        if action == 'exchange_token' and 'code' not in parameters:
            return False, "exchange_token action requires: authorization code"

        return True, ""

    def get_capability_description(self) -> str:
        """Return skill description"""
        return (
            f"LinkedIn MCP Action Skill (v{self.version}): "
            f"Creates LinkedIn posts via MCP server at {self.mcp_url}. "
            f"Actions: create_post, create_draft, check_draft, execute_draft, get_auth_url, exchange_token"
        )

    def _call_mcp(self, endpoint: str, data: Optional[Dict] = None, method: str = 'post') -> Dict:
        """Make a request to the MCP server"""
        url = f"{self.mcp_url}/{endpoint}"
        try:
            if method == 'get':
                response = requests.get(url, timeout=self.timeout)
            else:
                response = requests.post(url, json=data, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"MCP request failed: {str(e)}",
                "endpoint": endpoint
            }

    def _create_post(self, text: str, visibility: str = "PUBLIC",
                     images: Optional[List[str]] = None) -> Dict:
        """Create a post on LinkedIn (or draft file on cloud)"""
        from agent_config import is_cloud
        if is_cloud():
            return self._create_draft_file(text, visibility)

        data = {
            "text": text,
            "visibility": visibility,
            "images": images or []
        }

        result = self._call_mcp('create_post', data)

        if result.get("success"):
            return {
                "success": True,
                "action": "create_post",
                "post_id": result.get("post_id"),
                "post_url": result.get("post_url"),
                "message": result.get("message", "Post created")
            }
        return result

    def _create_draft_file(self, text: str, visibility: str = "PUBLIC") -> Dict:
        """Create a draft file in Pending_Approval/social/ (used by cloud agent)."""
        vault_path = os.getenv("VAULT_PATH", r"D:\prompteng\AI_Employee_Vault")
        draft_dir = Path(vault_path) / "Pending_Approval" / "social"
        draft_dir.mkdir(parents=True, exist_ok=True)

        from agent_config import AGENT_ID
        now = datetime.now()
        filename = f"SOCIAL_DRAFT_linkedin_{now.strftime('%Y%m%d_%H%M%S')}.md"
        filepath = draft_dir / filename

        content = f"""---
type: social_post
action: create_post
platform: linkedin
visibility: {visibility}
created_by: {AGENT_ID}
created_at: {now.isoformat()}
status: pending_approval
---

## LinkedIn Post Draft

### Content
{text}

---
*Draft created by Cloud Agent. Approve to post.*
"""
        filepath.write_text(content, encoding="utf-8")
        return {
            "success": True,
            "action": "draft_file",
            "filepath": str(filepath),
            "filename": filename,
            "status": "pending_approval",
            "message": "Draft file created for linkedin (cloud mode)",
        }

    def _create_draft(self, text: str, visibility: str = "PUBLIC") -> Dict:
        """Create a draft LinkedIn post for approval"""
        data = {
            "text": text,
            "visibility": visibility
        }

        result = self._call_mcp('create_draft', data)

        if result.get("success"):
            return {
                "success": True,
                "action": "create_draft",
                "filepath": result.get("filepath"),
                "filename": Path(result.get("filepath", '')).name,
                "status": "pending_approval"
            }
        return result

    def _check_draft_status(self, filename: str) -> Dict:
        """Check draft approval status"""
        data = {"filename": filename}
        result = self._call_mcp('check_draft_status', data)

        if result.get("success") or result.get("status") in ["approved", "rejected", "pending"]:
            return {
                "success": True,
                "action": "check_draft",
                "filename": filename,
                "status": result.get("status"),
                "location": result.get("location")
            }
        return result

    def _execute_draft(self, filename: str) -> Dict:
        """Execute an approved draft LinkedIn post"""
        data = {"filename": filename}
        result = self._call_mcp('execute_approved_draft', data)

        if result.get("success"):
            return {
                "success": True,
                "action": "execute_draft",
                "filename": filename,
                "post_id": result.get("post_id"),
                "post_url": result.get("post_url"),
                "message": result.get("message", "Post published")
            }
        return result

    def _get_auth_url(self) -> Dict:
        """Get LinkedIn OAuth authorization URL"""
        result = self._call_mcp('get_auth_url', method='get')

        if result.get("success"):
            return {
                "success": True,
                "action": "get_auth_url",
                "authorization_url": result.get("authorization_url"),
                "instructions": result.get("instructions", "Open URL to authorize")
            }
        return result

    def _exchange_token(self, code: str) -> Dict:
        """Exchange authorization code for access token"""
        data = {"code": code}
        result = self._call_mcp('exchange_token', data)

        if result.get("success"):
            return {
                "success": True,
                "action": "exchange_token",
                "expires_at": result.get("expires_at"),
                "person_urn": result.get("person_urn"),
                "message": "Token obtained successfully"
            }
        return result

    def _get_capabilities(self) -> Dict:
        """Get MCP server capabilities"""
        result = self._call_mcp('capabilities', method='get')
        return {
            "success": True,
            "action": "capabilities",
            "capabilities": result
        }

    def execute(self, context: Dict[str, Any], parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the LinkedIn MCP action skill.

        Parameters:
        - action: One of 'create_post', 'create_draft', 'check_draft', 'execute_draft', 'get_auth_url', 'exchange_token', 'capabilities'
        - text: Post content (for create_post, create_draft)
        - visibility: PUBLIC or CONNECTIONS_ONLY (optional, default: PUBLIC)
        - images: List of image URLs or paths (optional, for create_post)
        - filename: Draft filename (for check_draft, execute_draft)
        - code: Authorization code (for exchange_token)

        Returns:
        - Dictionary with LinkedIn operation results
        """
        action = parameters.get('action')

        if action == 'create_post':
            return self._create_post(
                text=parameters['text'],
                visibility=parameters.get('visibility', 'PUBLIC'),
                images=parameters.get('images', [])
            )

        elif action == 'create_draft':
            return self._create_draft(
                text=parameters['text'],
                visibility=parameters.get('visibility', 'PUBLIC')
            )

        elif action == 'check_draft':
            return self._check_draft_status(parameters['filename'])

        elif action == 'execute_draft':
            return self._execute_draft(parameters['filename'])

        elif action == 'get_auth_url':
            return self._get_auth_url()

        elif action == 'exchange_token':
            return self._exchange_token(parameters['code'])

        elif action == 'capabilities':
            return self._get_capabilities()

        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}"
            }


# Auto-register the skill when module is imported
def _register():
    from ..registry import register_skill
    register_skill(LinkedInMCPActionSkill, "linkedin_mcp_action")

_register()
