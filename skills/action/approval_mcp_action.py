"""
Approval MCP Action Skill
Manages human-in-the-loop approvals via the Approval MCP server
"""

import requests
from typing import Any, Dict

from .. import AgentSkill


class ApprovalMCPActionSkill(AgentSkill):
    """
    Skill for managing human approvals via the Approval MCP server.
    
    Capabilities:
    - Request human approval for sensitive actions
    - Check approval status
    - List pending approvals
    - Approve/reject actions (for human use)
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        config = config or {}
        config.setdefault('mcp_url', 'http://localhost:8003')
        config.setdefault('timeout', 30)
        super().__init__(config)
        
        self.mcp_url = self.config.get('mcp_url', 'http://localhost:8003')
        self.timeout = self.config.get('timeout', 30)
    
    def validate_inputs(self, parameters: Dict[str, Any]) -> tuple:
        """Validate input parameters"""
        action = parameters.get('action')
        if not action:
            return False, "Missing required parameter: action"
        
        valid_actions = ['request', 'check', 'list', 'approve', 'reject']
        if action not in valid_actions:
            return False, f"Invalid action. Must be one of: {valid_actions}"
        
        if action == 'request' and not all(k in parameters for k in ['action_type', 'amount', 'reason']):
            return False, "Request action requires: action_type, amount, reason"
        
        if action == 'check' and 'request_id' not in parameters:
            return False, "Check action requires: request_id"
        
        if action in ['approve', 'reject'] and 'request_id' not in parameters:
            return False, f"{action} action requires: request_id"
        
        return True, ""
    
    def get_capability_description(self) -> str:
        """Return skill description"""
        return (
            f"Approval MCP Action Skill (v{self.version}): "
            f"Manages human approvals via MCP server at {self.mcp_url}. "
            f"Actions: request, check, list, approve, reject"
        )
    
    def _call_mcp(self, endpoint: str, data: Dict) -> Dict:
        """Make a request to the MCP server"""
        url = f"{self.mcp_url}/{endpoint}"
        try:
            if endpoint == 'list_pending_approvals':
                response = requests.get(url, timeout=self.timeout)
            else:
                response = requests.post(url, json=data, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"MCP request failed: {str(e)}"
            }
    
    def _request_approval(self, action_type: str, amount: str, 
                          recipient: str, reason: str) -> Dict:
        """Request human approval"""
        result = self._call_mcp('request_approval', {
            "action": action_type,
            "amount": amount,
            "recipient": recipient,
            "reason": reason
        })
        
        if result.get("success"):
            return {
                "success": True,
                "action": "request",
                "request_id": result.get("request_id"),
                "filepath": result.get("filepath"),
                "status": "pending"
            }
        return result
    
    def _check_status(self, request_id: str) -> Dict:
        """Check approval status"""
        result = self._call_mcp('check_approval', {"request_id": request_id})
        
        if "status" in result:
            return {
                "success": True,
                "action": "check",
                "request_id": request_id,
                "status": result.get("status")
            }
        return result
    
    def _list_pending(self) -> Dict:
        """List pending approvals"""
        result = self._call_mcp('list_pending_approvals', {})
        
        if "pending_approvals" in result:
            return {
                "success": True,
                "action": "list",
                "pending_approvals": result.get("pending_approvals"),
                "count": result.get("count", 0)
            }
        return result
    
    def _approve(self, request_id: str) -> Dict:
        """Approve an action"""
        result = self._call_mcp('approve_action', {"request_id": request_id})
        
        if result.get("success"):
            return {
                "success": True,
                "action": "approve",
                "request_id": request_id,
                "status": "approved"
            }
        return result
    
    def _reject(self, request_id: str) -> Dict:
        """Reject an action"""
        result = self._call_mcp('reject_action', {"request_id": request_id})
        
        if result.get("success"):
            return {
                "success": True,
                "action": "reject",
                "request_id": request_id,
                "status": "rejected"
            }
        return result
    
    def execute(self, context: Dict[str, Any], parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the approval MCP action skill.
        
        Parameters:
        - action: One of 'request', 'check', 'list', 'approve', 'reject'
        - action_type: Type of action requiring approval (for request)
        - amount: Amount involved (for request)
        - recipient: Recipient of action (for request)
        - reason: Reason for action (for request)
        - request_id: Approval request ID (for check, approve, reject)
        
        Returns:
        - Dictionary with approval operation results
        """
        action = parameters.get('action')
        
        if action == 'request':
            return self._request_approval(
                parameters.get('action_type', ''),
                parameters.get('amount', 'N/A'),
                parameters.get('recipient', 'N/A'),
                parameters.get('reason', 'N/A')
            )
        
        elif action == 'check':
            return self._check_status(parameters['request_id'])
        
        elif action == 'list':
            return self._list_pending()
        
        elif action == 'approve':
            return self._approve(parameters['request_id'])
        
        elif action == 'reject':
            return self._reject(parameters['request_id'])
        
        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}"
            }


# Auto-register the skill when module is imported
def _register():
    from ..registry import register_skill
    register_skill(ApprovalMCPActionSkill, "approval_mcp_action")

_register()
