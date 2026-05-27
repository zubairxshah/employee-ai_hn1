# Claude Vault Connection Setup

## Overview
This document describes how to connect Claude Code to the Obsidian vault for the AI Personal Employee system.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Claude Code   │────▶│  Vault Connector │────▶│   MCP Servers   │
│   (Reasoning)   │◀────│   (Interface)    │◀────│  (File/Approval)│
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
                                               ┌─────────────────┐
                                               │  Obsidian Vault │
                                               │  (D:\prompteng\ │
                                               │  AI_Employee_   │
                                               │  Vault)         │
                                               └─────────────────┘
```

## Components

### 1. MCP Servers
Two HTTP servers that provide file system and approval functionality:

| Server | Port | Purpose |
|--------|------|---------|
| Filesystem MCP | 8000 | Read/write/move files in vault |
| Approval MCP | 8003 | Human-in-the-loop approval system |

### 2. Claude Vault Connector
Python module (`claude_vault_connector.py`) that provides a simple interface for Claude to interact with the vault through MCP servers.

### 3. Configuration
- `.claude/config.json` - Claude Code configuration with MCP server URLs
- `.claude/vault_integration.json` - Vault integration settings

## Quick Start

### Step 1: Install Dependencies
```bash
uv pip install -r requirements.txt
```

### Step 2: Start MCP Servers
```bash
python start_mcp_servers.py
```

Or start individual servers:
```bash
python mcp_servers\filesystem_mcp.py
python mcp_servers\approval_mcp.py
```

### Step 3: Test Connection
```bash
python test_claude_vault_connection.py
```

### Step 4: Use the Connector
```bash
# Check server status
python claude_vault_connector.py status

# Read dashboard
python claude_vault_connector.py dashboard

# List files in Needs_Action
python claude_vault_connector.py list Needs_Action

# Read a specific file
python claude_vault_connector.py read Needs_Action/some_task.md

# Request approval for an action
python claude_vault_connector.py approve "Payment" "$500" "Vendor" "Invoice #123"
```

## API Reference

### ClaudeVaultConnector Methods

| Method | Description |
|--------|-------------|
| `check_mcp_servers()` | Check if MCP servers are running |
| `read_file(path)` | Read a file from the vault |
| `write_file(path, content)` | Write content to a file |
| `list_files(path)` | List files in a directory |
| `move_file(source, dest)` | Move a file within the vault |
| `request_approval(action, amount, recipient, reason)` | Request human approval |
| `check_approval_status(request_id)` | Check approval status |
| `get_dashboard()` | Get dashboard content |
| `get_company_handbook()` | Get company handbook |
| `list_needs_action()` | List items needing action |
| `create_task_plan(name, steps, context)` | Create a task plan |
| `update_dashboard(updates)` | Update dashboard |

## Vault Structure

```
D:\prompteng\AI_Employee_Vault\
├── Dashboard.md              # Central monitoring dashboard
├── Company_Handbook.md       # Business rules and policies
├── Inbox\                    # New items received
├── Needs_Action\             # Items requiring processing
├── Done\                     # Completed tasks
├── Pending_Approval\         # Awaiting human approval
├── Approved\                 # Approved items
├── Rejected\                 # Rejected items
└── Plans\                    # Task plans
```

## Security Features

1. **Vault Boundaries**: All file operations restricted to vault directory
2. **Human-in-the-Loop**: Sensitive actions require approval
3. **Audit Logging**: All operations logged for traceability
4. **Input Sanitization**: All inputs sanitized before processing
5. **Rate Limiting**: Configurable rate limits on operations

## Troubleshooting

### MCP Servers Not Starting
1. Check if ports 8000 and 8003 are available
2. Verify Flask is installed: `pip install flask`
3. Check for import errors in server logs

### Connection Refused Errors
1. Ensure MCP servers are running
2. Check firewall settings
3. Verify localhost is accessible

### File Operations Failing
1. Verify vault path exists
2. Check file permissions
3. Ensure file is not locked by another process

### Approval System Not Working
1. Verify Pending_Approval directory exists
2. Check approval MCP server is running on port 8003
3. Verify file system permissions

## Integration with Claude Code

To use this integration with Claude Code:

1. Configure Claude to use the vault connector as a tool
2. Set up prompts that reference the Company Handbook rules
3. Enable the Ralph Wiggum loop for continuous task processing
4. Monitor the Dashboard.md for status updates

## Example Workflow

1. **Watcher detects new email** → Creates file in `Needs_Action/`
2. **Claude reads file** → Uses connector to read content
3. **Claude processes task** → Applies company handbook rules
4. **Claude creates plan** → Writes to `Plans/` directory
5. **Claude executes action** → Uses MCP to move file to `Done/`
6. **Dashboard updated** → Reflects completed task

## Next Steps

After setting up the connection:
1. Configure watcher scripts (Gmail, WhatsApp, Filesystem)
2. Set up the orchestrator to manage all components
3. Test the complete workflow end-to-end
4. Progress through development tiers (see TIER_INFO.md)
