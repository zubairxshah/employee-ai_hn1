# AI Personal Employee Architecture Documentation

## Overview
This document describes the complete architecture of the AI Personal Employee system, which implements the Perception → Reasoning → Action cycle using Claude Code as the reasoning engine.

## System Components

### 1. Perception Layer (The "Watchers")
The Perception layer serves as the AI Employee's sensory system, continuously monitoring various inputs and creating actionable files for Claude to process.

#### Core Watcher Pattern
All watchers inherit from the `BaseWatcher` class and follow this pattern:
- Continuously monitor a specific input source
- Detect new or changed items requiring attention
- Create structured `.md` files in the `/Needs_Action` folder
- Include metadata and suggested actions in the file

#### Available Watchers

**Gmail Watcher (`gmail_watcher.py`)**
- Monitors Gmail for important/unread messages
- Filters for messages marked as important
- Creates action files with email content and suggested responses
- Tracks processed messages to avoid duplicates

**WhatsApp Watcher (`whatsapp_watcher.py`)**
- Monitors WhatsApp Web for messages containing specific keywords
- Keywords include: 'urgent', 'asap', 'invoice', 'payment', 'help'
- Creates action files for high-priority messages
- Uses Playwright for web automation

**File System Watcher (`filesystem_watcher.py`)**
- Monitors a designated drop folder for new files
- Processes specific file types (PDF, DOCX, TXT, XLSX, images)
- Creates metadata files with file details and suggested actions
- Uses the watchdog library for efficient file monitoring

### 2. Reasoning Layer (Claude Code)
The Reasoning layer uses Claude Code to process tasks and make decisions based on the company handbook rules.

#### Claude Integration
- Claude reads files from the `/Needs_Action` folder
- Applies rules from `Company_Handbook.md` to guide decisions
- Creates `Plan.md` files outlining next steps
- Updates `Dashboard.md` with current status

#### Ralph Wiggum Loop
The Ralph Wiggum loop ensures tasks are completed by:
- Monitoring for completion indicators (promises or file movements)
- Continuing processing until tasks are truly complete
- Providing visibility into Claude's previous attempts
- Preventing premature exits from incomplete tasks

### 3. Action Layer (The "Hands")
The Action layer uses Model Context Protocol (MCP) servers to perform external actions.

#### Available MCP Servers

**Filesystem MCP (`filesystem_mcp.py`)**
- Port: 8000
- Provides file operations: read, write, list, move
- Enforces vault boundaries for security
- Enables Claude to manipulate files in the Obsidian vault

**Approval MCP (`approval_mcp.py`)**
- Port: 8003
- Manages human-in-the-loop approval process
- Creates approval request files for sensitive actions
- Tracks approval status (pending, approved, rejected)

### 4. Persistence Layer (The "Memory")
The Persistence layer maintains state and provides long-term memory using the Obsidian vault.

#### Vault Structure
```
/Vault/
├── Dashboard.md          # Real-time summary
├── Company_Handbook.md   # Rules of engagement
├── Inbox/               # New items from watchers
├── Needs_Action/        # Items requiring processing
├── Done/                # Completed tasks
├── Pending_Approval/    # Items awaiting human approval
├── Approved/            # Approved items
└── Rejected/            # Rejected items
```

## Operation Flow

### Normal Operation
1. **Perception**: Watchers detect new inputs and create files in `/Needs_Action`
2. **Reasoning**: Claude processes files, applies company rules, creates plans
3. **Action**: Claude uses MCP servers to perform external actions
4. **Persistence**: Results are saved back to the vault, files moved to `/Done`

### Human-in-the-Loop Operation
1. **Detection**: Claude identifies sensitive action (e.g., payment over $500)
2. **Request**: Claude creates approval request in `/Pending_Approval`
3. **Review**: Human reviews and moves file to `/Approved` or `/Rejected`
4. **Execution**: MCP server detects approval and executes action

### Ralph Wiggum Loop Operation
1. **Initiation**: Task begins with initial prompt
2. **Processing**: Claude works on the task
3. **Checking**: Stop hook checks for completion indicators
4. **Continuation**: If incomplete, prompt is reinjected for continued work
5. **Completion**: Loop ends when task is fully completed

## Security & Safety Measures

### Vault Boundaries
- All file operations restricted to vault directory
- MCP servers enforce path validation
- Prevents unauthorized file system access

### Human Oversight
- Approval system for sensitive actions
- Clear audit trails for all operations
- Company handbook rules enforced automatically

### Error Handling
- Graceful degradation when components fail
- Comprehensive logging for debugging
- Retry mechanisms for transient failures

## Configuration

### MCP Server Configuration (`mcp_config.json`)
Defines available MCP servers and their connection parameters.

### Claude Integration (`~/.config/claude-code/mcp.json`)
Configures Claude to connect to MCP servers.

### Vault Integration (`~/.claude/vault_integration.json`)
Sets up Claude to work with the Obsidian vault.

## Deployment Options

### Local Development
- All components run locally
- Direct file system access to vault
- Suitable for development and testing

### Production Deployment
- MCP servers may run on separate machines
- Secure credential management
- Monitoring and health checks

## Troubleshooting

### Common Issues
- Watchers not detecting changes: Check file permissions and paths
- Claude not processing files: Verify vault integration configuration
- MCP servers not responding: Check firewall and network connectivity

### Debugging Tips
- Enable detailed logging in all components
- Monitor the vault directories for expected file creation/movement
- Check MCP server status and logs