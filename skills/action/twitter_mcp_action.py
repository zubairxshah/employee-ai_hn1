"""
Twitter (X) MCP Action Skill
Provides Twitter posting capabilities via the Twitter MCP server
"""

import os
import requests
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

from .. import AgentSkill


class TwitterMCPActionSkill(AgentSkill):
    """
    Skill for creating tweets via the Twitter MCP server.

    Capabilities:
    - Create tweets (max 280 characters)
    - Create draft tweets for approval
    - Check draft approval status
    - Execute approved drafts
    - Get engagement summary
    - OAuth 2.0 + PKCE authentication management
    - Token refresh
    """

    def __init__(self, config: Dict[str, Any] = None):
        config = config or {}
        config.setdefault('mcp_url', 'http://localhost:8007')
        config.setdefault('timeout', 30)
        config.setdefault('max_tweet_length', 280)
        super().__init__(config)

        self.mcp_url = self.config.get('mcp_url', 'http://localhost:8007')
        self.timeout = self.config.get('timeout', 30)
        self.max_tweet_length = self.config.get('max_tweet_length', 280)

    def validate_inputs(self, parameters: Dict[str, Any]) -> tuple:
        """Validate input parameters"""
        action = parameters.get('action')
        if not action:
            return False, "Missing required parameter: action"

        valid_actions = [
            'create_tweet', 'create_draft', 'check_draft', 'execute_draft',
            'get_engagement_summary', 'get_auth_url', 'exchange_token',
            'refresh_token', 'capabilities'
        ]
        if action not in valid_actions:
            return False, f"Invalid action. Must be one of: {valid_actions}"

        if action in ('create_tweet', 'create_draft'):
            if 'text' not in parameters:
                return False, f"{action} action requires: text"
            if len(parameters['text']) > self.max_tweet_length:
                return False, f"Tweet exceeds {self.max_tweet_length} character limit"

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
            f"Twitter MCP Action Skill (v{self.version}): "
            f"Creates tweets via MCP server at {self.mcp_url}. "
            f"Max tweet length: {self.max_tweet_length}. "
            f"Actions: create_tweet, create_draft, check_draft, execute_draft, "
            f"get_engagement_summary, get_auth_url, exchange_token, refresh_token"
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

    def _create_tweet(self, text: str) -> Dict:
        """Create a tweet (or draft file on cloud)"""
        from agent_config import is_cloud
        if is_cloud():
            return self._create_draft_file(text)

        data = {"text": text}
        result = self._call_mcp('create_tweet', data)

        if result.get("success"):
            return {
                "success": True,
                "action": "create_tweet",
                "tweet_id": result.get("tweet_id"),
                "tweet_url": result.get("tweet_url"),
                "message": result.get("message", "Tweet created")
            }
        return result

    def _create_draft_file(self, text: str) -> Dict:
        """Create a draft file in Pending_Approval/social/ (used by cloud agent)."""
        vault_path = os.getenv("VAULT_PATH", r"D:\prompteng\AI_Employee_Vault")
        draft_dir = Path(vault_path) / "Pending_Approval" / "social"
        draft_dir.mkdir(parents=True, exist_ok=True)

        from agent_config import AGENT_ID
        now = datetime.now()
        filename = f"SOCIAL_DRAFT_twitter_{now.strftime('%Y%m%d_%H%M%S')}.md"
        filepath = draft_dir / filename

        content = f"""---
type: social_post
action: create_tweet
platform: twitter
created_by: {AGENT_ID}
created_at: {now.isoformat()}
status: pending_approval
char_count: {len(text)}
---

## Tweet Draft

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
            "char_count": len(text),
            "status": "pending_approval",
            "message": "Draft file created for twitter (cloud mode)",
        }

    def _create_draft(self, text: str) -> Dict:
        """Create a draft tweet for approval"""
        data = {"text": text}
        result = self._call_mcp('create_draft', data)

        if result.get("success"):
            return {
                "success": True,
                "action": "create_draft",
                "filepath": result.get("filepath"),
                "filename": result.get("filename"),
                "char_count": result.get("char_count"),
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
        """Execute an approved draft tweet"""
        data = {"filename": filename}
        result = self._call_mcp('execute_approved_draft', data)

        if result.get("success"):
            return {
                "success": True,
                "action": "execute_draft",
                "filename": filename,
                "tweet_id": result.get("tweet_id"),
                "tweet_url": result.get("tweet_url"),
                "message": result.get("message", "Tweet published")
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
        """Get Twitter OAuth authorization URL"""
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
                "username": result.get("username"),
                "expires_at": result.get("expires_at"),
                "message": "Token obtained successfully"
            }
        return result

    def _refresh_token(self) -> Dict:
        """Refresh the access token"""
        result = self._call_mcp('refresh_token')

        if result.get("success"):
            return {
                "success": True,
                "action": "refresh_token",
                "expires_at": result.get("expires_at"),
                "message": "Token refreshed"
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
        Execute the Twitter MCP action skill.

        Parameters:
        - action: One of the valid actions
        - text: Tweet content (for create_tweet, create_draft)
        - filename: Draft filename (for check_draft, execute_draft)
        - code: Authorization code (for exchange_token)
        """
        action = parameters.get('action')

        if action == 'create_tweet':
            return self._create_tweet(text=parameters['text'])

        elif action == 'create_draft':
            return self._create_draft(text=parameters['text'])

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

        elif action == 'refresh_token':
            return self._refresh_token()

        elif action == 'capabilities':
            return self._get_capabilities()

        else:
            return {"success": False, "error": f"Unknown action: {action}"}


# Auto-register the skill when module is imported
def _register():
    from ..registry import register_skill
    register_skill(TwitterMCPActionSkill, "twitter_mcp_action")

_register()
