"""
Facebook/Instagram MCP Action Skill
Provides Facebook Page and Instagram posting capabilities via the Facebook MCP server
"""

import os
import requests
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

from .. import AgentSkill


class FacebookMCPActionSkill(AgentSkill):
    """
    Skill for creating Facebook/Instagram posts via the Facebook MCP server.

    Capabilities:
    - Create posts on Facebook Pages
    - Create posts on Instagram
    - Create draft posts for approval
    - Check draft approval status
    - Execute approved drafts
    - Get engagement summary
    - OAuth authentication management
    """

    def __init__(self, config: Dict[str, Any] = None):
        config = config or {}
        config.setdefault('mcp_url', 'http://localhost:8006')
        config.setdefault('timeout', 30)
        super().__init__(config)

        self.mcp_url = self.config.get('mcp_url', 'http://localhost:8006')
        self.timeout = self.config.get('timeout', 30)

    def validate_inputs(self, parameters: Dict[str, Any]) -> tuple:
        """Validate input parameters"""
        action = parameters.get('action')
        if not action:
            return False, "Missing required parameter: action"

        valid_actions = [
            'create_post', 'create_instagram_post', 'create_draft',
            'check_draft', 'execute_draft', 'get_engagement_summary',
            'get_auth_url', 'exchange_token', 'capabilities'
        ]
        if action not in valid_actions:
            return False, f"Invalid action. Must be one of: {valid_actions}"

        if action == 'create_post':
            if 'message' not in parameters and 'text' not in parameters:
                return False, "create_post action requires: message or text"

        if action == 'create_instagram_post':
            if 'caption' not in parameters and 'text' not in parameters:
                return False, "create_instagram_post action requires: caption or text"
            if 'image_url' not in parameters:
                return False, "create_instagram_post action requires: image_url"

        if action == 'create_draft':
            if 'text' not in parameters:
                return False, "create_draft action requires: text"

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
            f"Facebook/Instagram MCP Action Skill (v{self.version}): "
            f"Creates Facebook/Instagram posts via MCP server at {self.mcp_url}. "
            f"Actions: create_post, create_instagram_post, create_draft, check_draft, "
            f"execute_draft, get_engagement_summary, get_auth_url, exchange_token"
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

    def _create_post(self, message: str) -> Dict:
        """Create a post on Facebook Page (or draft file on cloud)"""
        from agent_config import is_cloud
        if is_cloud():
            return self._create_draft_file("facebook", message)

        data = {"message": message}
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

    def _create_instagram_post(self, caption: str, image_url: str) -> Dict:
        """Create a post on Instagram (or draft file on cloud)"""
        from agent_config import is_cloud
        if is_cloud():
            return self._create_draft_file("instagram", caption, image_url)

        data = {"caption": caption, "image_url": image_url}
        result = self._call_mcp('create_instagram_post', data)

        if result.get("success"):
            return {
                "success": True,
                "action": "create_instagram_post",
                "post_id": result.get("post_id"),
                "message": result.get("message", "Instagram post created")
            }
        return result

    def _create_draft_file(self, platform: str, text: str, image_url: str = "") -> Dict:
        """Create a draft file in Pending_Approval/social/ (used by cloud agent)."""
        vault_path = os.getenv("VAULT_PATH", r"D:\prompteng\AI_Employee_Vault")
        draft_dir = Path(vault_path) / "Pending_Approval" / "social"
        draft_dir.mkdir(parents=True, exist_ok=True)

        from agent_config import AGENT_ID
        now = datetime.now()
        filename = f"SOCIAL_DRAFT_{platform}_{now.strftime('%Y%m%d_%H%M%S')}.md"
        filepath = draft_dir / filename

        content = f"""---
type: social_post
action: create_post
platform: {platform}
created_by: {AGENT_ID}
created_at: {now.isoformat()}
status: pending_approval
image_url: {image_url}
---

## Social Media Draft ({platform.title()})

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
            "message": f"Draft file created for {platform} (cloud mode)",
        }

    def _create_draft(self, text: str, platform: str = "facebook",
                      image_url: str = "") -> Dict:
        """Create a draft post for approval"""
        data = {"text": text, "platform": platform, "image_url": image_url}
        result = self._call_mcp('create_draft', data)

        if result.get("success"):
            return {
                "success": True,
                "action": "create_draft",
                "filepath": result.get("filepath"),
                "filename": result.get("filename"),
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
        """Execute an approved draft post"""
        data = {"filename": filename}
        result = self._call_mcp('execute_approved_draft', data)

        if result.get("success"):
            return {
                "success": True,
                "action": "execute_draft",
                "filename": filename,
                "post_id": result.get("post_id"),
                "message": result.get("message", "Post published")
            }
        return result

    def _get_engagement_summary(self) -> Dict:
        """Get engagement summary"""
        result = self._call_mcp('get_engagement_summary', method='get')
        if result.get("success"):
            return {
                "success": True,
                "action": "get_engagement_summary",
                "summary": result
            }
        return result

    def _get_auth_url(self) -> Dict:
        """Get Facebook OAuth authorization URL"""
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
                "page_id": result.get("page_id"),
                "instagram_account_id": result.get("instagram_account_id"),
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
        Execute the Facebook/Instagram MCP action skill.

        Parameters:
        - action: One of the valid actions
        - message/text: Post content (for create_post)
        - caption: Instagram caption (for create_instagram_post)
        - image_url: Image URL (for create_instagram_post, create_draft)
        - platform: 'facebook' or 'instagram' (for create_draft)
        - filename: Draft filename (for check_draft, execute_draft)
        - code: Authorization code (for exchange_token)
        """
        action = parameters.get('action')

        if action == 'create_post':
            return self._create_post(
                message=parameters.get('message') or parameters.get('text', '')
            )

        elif action == 'create_instagram_post':
            return self._create_instagram_post(
                caption=parameters.get('caption') or parameters.get('text', ''),
                image_url=parameters['image_url']
            )

        elif action == 'create_draft':
            return self._create_draft(
                text=parameters['text'],
                platform=parameters.get('platform', 'facebook'),
                image_url=parameters.get('image_url', '')
            )

        elif action == 'check_draft':
            return self._check_draft_status(parameters['filename'])

        elif action == 'execute_draft':
            return self._execute_draft(parameters['filename'])

        elif action == 'get_engagement_summary':
            return self._get_engagement_summary()

        elif action == 'get_auth_url':
            return self._get_auth_url()

        elif action == 'exchange_token':
            return self._exchange_token(parameters['code'])

        elif action == 'capabilities':
            return self._get_capabilities()

        else:
            return {"success": False, "error": f"Unknown action: {action}"}


# Auto-register the skill when module is imported
def _register():
    from ..registry import register_skill
    register_skill(FacebookMCPActionSkill, "facebook_mcp_action")

_register()
