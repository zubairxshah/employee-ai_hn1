# End-to-End Workflow Guide

## Overview
This guide explains how to test and run the complete AI Personal Employee workflow: **Perception → Reasoning → Action → Persistence**.

## Test Results
```
[SUCCESS] End-to-end workflow test PASSED!

Workflow Stages:
  [OK] 1. PERCEPTION - Watcher created task file
  [OK] 2. REASONING  - Claude analyzed and created plan
  [OK] 3. ACTION     - Executed with human approval
  [OK] 4. PERSISTENCE - Dashboard updated
  [OK] 5. VERIFICATION - All checks passed
```

---

## How to Run the Workflow Test

### Prerequisites
1. Python 3.8+ installed
2. Dependencies installed: `uv pip install -r requirements.txt`
3. Obsidian vault at: `D:\prompteng\AI_Employee_Vault`

### Step 1: Start MCP Servers
```bash
python start_mcp_servers.py
```

Expected output:
```
============================================================
AI Personal Employee - MCP Server Launcher
============================================================
Starting Filesystem MCP server on port 8000...
[OK] Filesystem MCP server started successfully (PID: xxxx)
Starting Approval MCP server on port 8003...
[OK] Approval MCP server started successfully (PID: xxxx)

============================================================
Successfully started 2 MCP server(s)

Server URLs:
  - filesystem: http://localhost:8000
  - approval: http://localhost:8003

Press Ctrl+C to stop all servers
```

**Keep this window open** - servers run in foreground.

### Step 2: Run the End-to-End Test
Open a **new terminal** and run:
```bash
python test_end_to_end_workflow.py
```

### Step 3: Review Results
The test will:
1. Create a simulated task (email requesting invoice)
2. Process the task through Claude's reasoning
3. Request and simulate human approval
4. Generate invoice and email
5. Update the dashboard
6. Verify all components completed

---

## Workflow Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    PERCEPTION LAYER (Watchers)                    │
│  - Gmail Watcher monitors for important emails                   │
│  - WhatsApp Watcher monitors for keyword messages                │
│  - Filesystem Watcher monitors drop folder                       │
│  - Creates .md files in Needs_Action/ directory                  │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                    REASONING LAYER (Claude Code)                  │
│  - Reads task files from Needs_Action/                           │
│  - Applies Company Handbook rules                                │
│  - Creates plans in Plans/ directory                             │
│  - Identifies actions requiring human approval                   │
│  - Ralph Wiggum loop ensures task completion                     │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                      ACTION LAYER (MCP Servers)                   │
│  - Filesystem MCP: Read/write/move files                         │
│  - Approval MCP: Human-in-the-loop approvals                     │
│  - Email MCP (future): Send emails                               │
│  - Browser MCP (future): Web automation                          │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                   PERSISTENCE LAYER (Obsidian Vault)              │
│  - Dashboard.md: Real-time status                                │
│  - Company_Handbook.md: Business rules                           │
│  - Inbox/: New items                                             │
│  - Needs_Action/: Pending tasks                                  │
│  - Done/: Completed tasks                                        │
│  - Pending_Approval/: Awaiting human decision                    │
│  - Approved/: Approved actions                                   │
│  - Rejected/: Rejected actions                                   │
│  - Plans/: Task plans                                            │
│  - Accounting/: Invoices and financial records                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## Manual Workflow Walkthrough

You can also run each step manually using the connector CLI:

### 1. Check Server Status
```bash
python claude_vault_connector.py status
```

### 2. View Dashboard
```bash
python claude_vault_connector.py dashboard
```

### 3. List Tasks Needing Action
```bash
python claude_vault_connector.py list Needs_Action
```

### 4. Read a Specific Task
```bash
python claude_vault_connector.py read Needs_Action/email_invoice_request_20260216_223959.md
```

### 5. View Task Plans
```bash
python claude_vault_connector.py list Plans
```

### 6. View Generated Invoices
```bash
python claude_vault_connector.py list Accounting
```

### 7. Request Human Approval (Manual)
```bash
python claude_vault_connector.py approve "Send Invoice" "$2500" "client@example.com" "Project Alpha completion"
```

---

## Real-World Usage

### Setting Up Real Watchers

#### Gmail Watcher
1. Obtain Gmail API credentials
2. Configure `watchers/perception/gmail_watcher.py`
3. Add to orchestrator

#### WhatsApp Watcher
1. Set up Playwright for browser automation
2. Configure keywords to monitor
3. Add to orchestrator

#### Filesystem Watcher
Already implemented - monitors drop folder for new files.

### Real Human Approval Workflow

Instead of simulation, humans physically move files:

1. **Approval Request Created** → File appears in `Pending_Approval/`
2. **Human Reviews** → Opens file, reads details
3. **Human Approves** → Moves file to `Approved/`
4. **Human Rejects** → Moves file to `Rejected/`
5. **Claude Detects** → Checks folder, proceeds accordingly

### Integrating Real Claude Code

To use actual Claude Code API:

1. Set up Claude API key in `.env`
2. Configure `.claude/config.json` with API settings
3. Update `claude_vault_connector.py` to call Claude API
4. Enable Ralph Wiggum loop for iterative processing

---

## Troubleshooting

### MCP Servers Won't Start
```bash
# Check if ports are in use
netstat -ano | findstr :8000
netstat -ano | findstr :8003

# Kill process if needed
taskkill /F /PID <pid>

# Restart servers
python start_mcp_servers.py
```

### Test Fails at Perception
- Ensure `Needs_Action/` directory exists
- Check write permissions on vault
- Verify MCP servers are running

### Test Fails at Reasoning
- Check task file format (YAML frontmatter)
- Verify Company Handbook exists in vault
- Review plan creation logic

### Test Fails at Action
- Ensure `Pending_Approval/` directory exists
- Check approval MCP server is running
- Verify file move permissions

### Test Fails at Persistence
- Check `Dashboard.md` exists
- Verify write permissions
- Ensure no file locks

---

## Production Deployment Checklist

- [ ] MCP servers running as Windows services
- [ ] Real Gmail watcher configured with credentials
- [ ] Real WhatsApp watcher configured with session
- [ ] Human approval workflow documented for users
- [ ] Claude Code API integrated
- [ ] Ralph Wiggum loop enabled for all tasks
- [ ] Audit logging enabled
- [ ] Rate limiting configured
- [ ] Error recovery mechanisms tested
- [ ] Security policies enforced

---

## Example Scenarios

### Scenario 1: Invoice Processing
1. **Perception**: Email arrives requesting invoice
2. **Reasoning**: Claude identifies amount, checks rules
3. **Action**: Requests approval, generates invoice, sends email
4. **Persistence**: Updates dashboard, archives task

### Scenario 2: Urgent WhatsApp Message
1. **Perception**: WhatsApp message with "urgent" keyword
2. **Reasoning**: Claude prioritizes, drafts response
3. **Action**: Requests approval for response content
4. **Persistence**: Logs conversation, updates dashboard

### Scenario 3: File Drop Processing
1. **Perception**: New PDF in drop folder
2. **Reasoning**: Claude analyzes document type
3. **Action**: Extracts data, files appropriately
4. **Persistence**: Updates indexes, notifies user

---

## Next Steps

After successful testing:

1. **Configure Real Watchers**
   - Set up Gmail API credentials
   - Configure WhatsApp session
   - Define drop folder location

2. **Customize Company Handbook**
   - Add your business rules
   - Define approval thresholds
   - Set response templates

3. **Enable Production Features**
   - Real email sending
   - Payment processing
   - Calendar integration

4. **Monitor and Optimize**
   - Review audit logs
   - Tune rate limits
   - Optimize Claude prompts

---

## Support

For issues or questions:
- Check `TROUBLESHOOTING_FAQ.md`
- Review `ERROR_RECOVERY.md`
- See `CLAUDE_VAULT_CONNECTION.md`
- Examine audit logs in vault
