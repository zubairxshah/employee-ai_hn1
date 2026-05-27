"""
Email MCP Action Skill
Provides email sending capabilities via the Email MCP server
"""

import os
import requests
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

from .. import AgentSkill


class EmailMCPActionSkill(AgentSkill):
    """
    Skill for sending emails via the Email MCP server.

    Capabilities:
    - Send emails via Gmail SMTP
    - Create draft emails for approval
    - Check draft approval status
    - Execute approved drafts
    - Support attachments
    """

    def __init__(self, config: Dict[str, Any] = None):
        config = config or {}
        config.setdefault('mcp_url', 'http://localhost:8001')
        config.setdefault('timeout', 30)
        super().__init__(config)

        self.mcp_url = self.config.get('mcp_url', 'http://localhost:8001')
        self.timeout = self.config.get('timeout', 30)

    def validate_inputs(self, parameters: Dict[str, Any]) -> tuple:
        """Validate input parameters"""
        action = parameters.get('action')
        if not action:
            return False, "Missing required parameter: action"

        valid_actions = ['send', 'draft', 'check_draft', 'execute_draft', 'capabilities']
        if action not in valid_actions:
            return False, f"Invalid action. Must be one of: {valid_actions}"

        if action == 'send':
            required = ['to', 'subject', 'body']
            for param in required:
                if param not in parameters:
                    return False, f"Send action requires: {', '.join(required)}"

        if action == 'draft':
            required = ['to', 'subject', 'body']
            for param in required:
                if param not in parameters:
                    return False, f"Draft action requires: {', '.join(required)}"

        if action == 'check_draft' and 'filename' not in parameters:
            return False, "check_draft action requires: filename"

        if action == 'execute_draft' and 'filename' not in parameters:
            return False, "execute_draft action requires: filename"

        return True, ""

    def get_capability_description(self) -> str:
        """Return skill description"""
        return (
            f"Email MCP Action Skill (v{self.version}): "
            f"Sends emails via MCP server at {self.mcp_url}. "
            f"Actions: send, draft, check_draft, execute_draft"
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

    def _send_email(self, to: str, subject: str, body: str,
                    html: bool = False, attachments: Optional[List[str]] = None) -> Dict:
        """Send an email (or create draft file if running on cloud)"""
        # Cloud agent: redirect to draft file instead of sending
        from agent_config import is_cloud
        if is_cloud():
            return self._create_draft_file("email", {
                "to": to, "subject": subject, "body": body,
                "action": "send_email",
            })

        data = {
            "to": to,
            "subject": subject,
            "body": body,
            "html": html,
            "attachments": attachments or []
        }

        result = self._call_mcp('send_email', data)

        if result.get("success"):
            return {
                "success": True,
                "action": "send",
                "to": to,
                "subject": subject,
                "message": result.get("message", "Email sent")
            }
        return result

    def _create_draft_file(self, domain: str, data: Dict) -> Dict:
        """Create a draft file in Pending_Approval/ (used by cloud agent)."""
        vault_path = os.getenv("VAULT_PATH", r"D:\prompteng\AI_Employee_Vault")
        draft_dir = Path(vault_path) / "Pending_Approval" / domain
        draft_dir.mkdir(parents=True, exist_ok=True)

        from agent_config import AGENT_ID
        now = datetime.now()
        filename = f"EMAIL_DRAFT_{now.strftime('%Y%m%d_%H%M%S')}.md"
        filepath = draft_dir / filename

        content = f"""---
type: send_email
action: {data.get('action', 'send_email')}
to: {data.get('to', '')}
subject: {data.get('subject', '')}
created_by: {AGENT_ID}
created_at: {now.isoformat()}
status: pending_approval
---

## Email Draft

**To:** {data.get('to', '')}
**Subject:** {data.get('subject', '')}

### Body
{data.get('body', '')}

---
*Draft created by Cloud Agent. Approve to send.*
"""
        filepath.write_text(content, encoding="utf-8")
        return {
            "success": True,
            "action": "draft_file",
            "filepath": str(filepath),
            "filename": filename,
            "status": "pending_approval",
            "message": "Draft file created (cloud mode)",
        }

    def _create_draft(self, to: str, subject: str, body: str, 
                      html: bool = False) -> Dict:
        """Create a draft email for approval"""
        data = {
            "to": to,
            "subject": subject,
            "body": body,
            "html": html
        }
        
        result = self._call_mcp('send_draft', data)
        
        if result.get("success"):
            return {
                "success": True,
                "action": "draft",
                "to": to,
                "subject": subject,
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
        """Execute an approved draft"""
        data = {"filename": filename}
        result = self._call_mcp('execute_approved_draft', data)
        
        if result.get("success"):
            return {
                "success": True,
                "action": "execute_draft",
                "filename": filename,
                "to": result.get("to"),
                "subject": result.get("subject"),
                "message": result.get("message", "Draft sent")
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
        Execute the email MCP action skill.

        Parameters:
        - action: One of 'send', 'draft', 'check_draft', 'execute_draft', 'capabilities'
        - to: Recipient email address (for send, draft)
        - subject: Email subject (for send, draft)
        - body: Email body content (for send, draft)
        - html: Whether body is HTML (optional, default: False)
        - attachments: List of attachment file paths (optional, for send)
        - filename: Draft filename (for check_draft, execute_draft)

        Returns:
        - Dictionary with email operation results
        """
        action = parameters.get('action')

        if action == 'send':
            return self._send_email(
                to=parameters['to'],
                subject=parameters['subject'],
                body=parameters['body'],
                html=parameters.get('html', False),
                attachments=parameters.get('attachments', [])
            )

        elif action == 'draft':
            return self._create_draft(
                to=parameters['to'],
                subject=parameters['subject'],
                body=parameters['body'],
                html=parameters.get('html', False)
            )

        elif action == 'check_draft':
            return self._check_draft_status(parameters['filename'])

        elif action == 'execute_draft':
            return self._execute_draft(parameters['filename'])

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
    register_skill(EmailMCPActionSkill, "email_mcp_action")

_register()
