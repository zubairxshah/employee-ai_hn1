"""
Claude Vault Connector
Provides a simple interface for Claude Code to interact with the Obsidian vault
through MCP servers.
"""

import requests
import json
import sys
from pathlib import Path
from datetime import datetime


class ClaudeVaultConnector:
    """Connects Claude Code to the Obsidian vault via MCP servers"""
    
    def __init__(self, vault_path: str = None):
        self.vault_path = vault_path or r"D:\prompteng\AI_Employee_Vault"
        self.filesystem_mcp_url = "http://localhost:8000"
        self.approval_mcp_url = "http://localhost:8003"
        
    def check_mcp_servers(self):
        """Check if MCP servers are running"""
        servers_status = {}
        
        # Check Filesystem MCP
        try:
            response = requests.get(f"{self.filesystem_mcp_url}/capabilities", timeout=5)
            servers_status["filesystem"] = {
                "status": "running",
                "url": self.filesystem_mcp_url,
                "capabilities": response.json() if response.status_code == 200 else None
            }
        except requests.exceptions.RequestException as e:
            servers_status["filesystem"] = {
                "status": "not_running",
                "url": self.filesystem_mcp_url,
                "error": str(e)
            }
        
        # Check Approval MCP
        try:
            response = requests.get(f"{self.approval_mcp_url}/list_pending_approvals", timeout=5)
            servers_status["approval"] = {
                "status": "running",
                "url": self.approval_mcp_url,
                "pending_count": response.json().get("count", 0) if response.status_code == 200 else 0
            }
        except requests.exceptions.RequestException as e:
            servers_status["approval"] = {
                "status": "not_running",
                "url": self.approval_mcp_url,
                "error": str(e)
            }
        
        return servers_status
    
    def read_file(self, relative_path: str) -> dict:
        """Read a file from the vault"""
        try:
            response = requests.post(
                f"{self.filesystem_mcp_url}/read_file",
                json={"path": relative_path},
                timeout=10
            )
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": str(e)}
    
    def write_file(self, relative_path: str, content: str) -> dict:
        """Write a file to the vault"""
        try:
            response = requests.post(
                f"{self.filesystem_mcp_url}/write_file",
                json={"path": relative_path, "content": content},
                timeout=10
            )
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": str(e)}
    
    def list_files(self, relative_path: str = ".") -> dict:
        """List files in a vault directory"""
        try:
            response = requests.post(
                f"{self.filesystem_mcp_url}/list_files",
                json={"path": relative_path},
                timeout=10
            )
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": str(e)}
    
    def move_file(self, source: str, destination: str) -> dict:
        """Move a file within the vault"""
        try:
            response = requests.post(
                f"{self.filesystem_mcp_url}/move_file",
                json={"source": source, "destination": destination},
                timeout=10
            )
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": str(e)}
    
    def request_approval(self, action: str, amount: str = "N/A", 
                        recipient: str = "N/A", reason: str = "N/A") -> dict:
        """Request human approval for a sensitive action"""
        try:
            response = requests.post(
                f"{self.approval_mcp_url}/request_approval",
                json={
                    "action": action,
                    "amount": amount,
                    "recipient": recipient,
                    "reason": reason
                },
                timeout=10
            )
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": str(e)}
    
    def check_approval_status(self, request_id: str) -> dict:
        """Check the status of an approval request"""
        try:
            response = requests.post(
                f"{self.approval_mcp_url}/check_approval",
                json={"request_id": request_id},
                timeout=10
            )
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": str(e)}
    
    def get_dashboard(self) -> dict:
        """Get the current dashboard content"""
        return self.read_file("Dashboard.md")
    
    def get_company_handbook(self) -> dict:
        """Get the company handbook content"""
        return self.read_file("Company_Handbook.md")
    
    def list_needs_action(self) -> dict:
        """List all items in the Needs_Action directory"""
        return self.list_files("Needs_Action")
    
    def create_task_plan(self, task_name: str, steps: list, context: str = "") -> dict:
        """Create a task plan file in the Plans directory"""
        plan_content = f"""---
type: task_plan
task: {task_name}
created: {datetime.now().isoformat()}
status: planned
---


# Task Plan: {task_name}

## Context
{context}

## Steps
"""
        for i, step in enumerate(steps, 1):
            plan_content += f"\n{i}. {step}\n"
        
        plan_content += "\n## Status\n- [ ] In Progress\n"
        
        return self.write_file(f"Plans/{task_name.replace(' ', '_')}_Plan.md", plan_content)
    
    def update_dashboard(self, updates: dict) -> dict:
        """Update the dashboard with new information"""
        # First read the current dashboard
        current = self.get_dashboard()
        
        if not current.get("success"):
            # Create a new dashboard if it doesn't exist
            dashboard_content = self._create_default_dashboard(updates)
        else:
            # Update the existing dashboard
            dashboard_content = self._update_dashboard_content(current.get("content", ""), updates)
        
        return self.write_file("Dashboard.md", dashboard_content)
    
    def _create_default_dashboard(self, updates: dict) -> str:
        """Create a default dashboard"""
        return f"""---
last_updated: {datetime.now().isoformat()}
status: active
---

# AI Employee Dashboard

## Overview
- **Status**: Active
- **Last Updated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Current Tasks
- No active tasks

## Recent Activity
- System initialized

## Pending Approvals
- None

## Notes
{json.dumps(updates, indent=2)}
"""
    
    def _update_dashboard_content(self, current_content: str, updates: dict) -> str:
        """Update existing dashboard content"""
        # Simple implementation - prepend update timestamp
        lines = current_content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('last_updated:'):
                lines[i] = f"last_updated: {datetime.now().isoformat()}"
                break
        
        return '\n'.join(lines)


def main():
    """CLI interface for the Claude Vault Connector"""
    connector = ClaudeVaultConnector()
    
    if len(sys.argv) < 2:
        print("Claude Vault Connector")
        print("=" * 40)
        print("Usage: python claude_vault_connector.py <command> [args]")
        print("\nCommands:")
        print("  status              - Check MCP server status")
        print("  list [path]         - List files in vault directory")
        print("  read <path>         - Read a file from the vault")
        print("  write <path>        - Write content to a file (stdin)")
        print("  move <src> <dst>    - Move a file within the vault")
        print("  dashboard           - Get dashboard content")
        print("  needs-action        - List items needing action")
        print("  approve <action> <amount> <recipient> <reason>")
        print("                        - Request approval for an action")
        return
    
    command = sys.argv[1]
    
    if command == "status":
        status = connector.check_mcp_servers()
        print(json.dumps(status, indent=2))
    
    elif command == "list":
        path = sys.argv[2] if len(sys.argv) > 2 else "."
        result = connector.list_files(path)
        print(json.dumps(result, indent=2))
    
    elif command == "read":
        if len(sys.argv) < 3:
            print("Error: Please provide a file path")
            return
        path = sys.argv[2]
        result = connector.read_file(path)
        if result.get("success"):
            print(result.get("content", ""))
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")
    
    elif command == "write":
        if len(sys.argv) < 3:
            print("Error: Please provide a file path")
            return
        path = sys.argv[2]
        content = sys.stdin.read()
        result = connector.write_file(path, content)
        print(json.dumps(result, indent=2))
    
    elif command == "move":
        if len(sys.argv) < 4:
            print("Error: Please provide source and destination paths")
            return
        source = sys.argv[2]
        dest = sys.argv[3]
        result = connector.move_file(source, dest)
        print(json.dumps(result, indent=2))
    
    elif command == "dashboard":
        result = connector.get_dashboard()
        if result.get("success"):
            print(result.get("content", ""))
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")
    
    elif command == "needs-action":
        result = connector.list_needs_action()
        print(json.dumps(result, indent=2))
    
    elif command == "approve":
        if len(sys.argv) < 6:
            print("Error: Usage: approve <action> <amount> <recipient> <reason>")
            return
        result = connector.request_approval(
            action=sys.argv[2],
            amount=sys.argv[3],
            recipient=sys.argv[4],
            reason=sys.argv[5]
        )
        print(json.dumps(result, indent=2))
    
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
