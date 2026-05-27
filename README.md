# Personal AI Employee

**Tagline:** Your life and business on autopilot. Local-first, agent-driven, human-in-the-loop.

## Overview
This project implements a "Digital FTE" (Full-Time Equivalent) - an AI agent powered by Claude Code and Obsidian that proactively manages personal and business affairs 24/7. Think of it as hiring a senior employee who figures out how to solve problems.

## Development Tiers
This project follows a tiered development approach:
- **Bronze Tier**: Foundation (Minimum Viable Deliverable) - 8-12 hours
- **Silver Tier**: Functional Assistant - 20-30 hours  
- **Gold Tier**: Autonomous Employee - 40+ hours
- **Platinum Tier**: Always-On Cloud + Local Executive - 60+ hours

See [TIER_INFO.md](TIER_INFO.md) for detailed requirements for each tier.

## Architecture & Tech Stack

### The Brain
- Claude Code acts as the reasoning engine
- Includes Ralph Wiggum Stop hook for continuous iteration until task completion

### The Memory/GUI
- Obsidian (local Markdown) serves as the management dashboard
- Keeps data local and accessible
- Vault located at: `D:\prompteng\AI_Employee_Vault`

### The Senses (Watchers)
- Lightweight Python scripts monitor Gmail, WhatsApp, and filesystems
- Trigger the AI when relevant events occur
- See `watchers/` directory for implementations

### The Hands (MCP)
- Model Context Protocol (MCP) servers handle external actions
- Manages email sending, button clicking, and other external operations

## Standout Feature
The "Monday Morning CEO Briefing" - the AI autonomously audits bank transactions and tasks to report revenue and bottlenecks, transforming the AI from a chatbot into a proactive business partner.

## Project Structure
- `.claude/` - Claude Code configuration files
- `.specify/` - Specifications and requirements documents
- `AGENTS.md` - Information about AI agents
- `CLAUDE.md` - Claude Code integration details
- `CLAUDE_INTEGRATION.md` - Claude integration layer specifications
- `AGENT_SKILLS.md` - Agent Skills framework documentation
- `MCP_SERVER.md` - Model Context Protocol server documentation
- `TIER_INFO.md` - Detailed tier requirements
- `Vault_Config.md` - Obsidian vault configuration
- `Dashboard.md` - Sample dashboard file
- `Company_Handbook.md` - Sample company handbook file
- `watchers/` - Watcher scripts (file system, Gmail, etc.)
- `requirements.txt` - Python dependencies

## Getting Started

### Quick Start
1. Install dependencies: `uv pip install -r requirements.txt`
2. Start MCP servers: `python start_mcp_servers.py`
3. Test connection: `python test_claude_vault_connection.py`
4. Use the connector: `python claude_vault_connector.py <command>`

### Full Setup
1. Install dependencies: `uv pip install -r requirements.txt`
2. Set up your Obsidian vault at `D:\prompteng\AI_Employee_Vault`
3. Copy `Dashboard.md` and `Company_Handbook.md` to your vault
4. Configure Claude API access in `.claude/config.json`
5. Start MCP servers: `python start_mcp_servers.py`
6. Test the connection: `python test_claude_vault_connection.py`
7. Start with Bronze Tier requirements

## Project Structure
- `.claude/` - Claude Code configuration files
- `.specify/` - Specifications and requirements documents
- `AGENTS.md` - Information about AI agents
- `CLAUDE.md` - Claude Code integration details
- `CLAUDE_INTEGRATION.md` - Claude integration layer specifications
- `AGENT_SKILLS.md` - Agent Skills framework documentation
- `MCP_SERVER.md` - Model Context Protocol server documentation
- `TIER_INFO.md` - Detailed tier requirements
- `Vault_Config.md` - Obsidian vault configuration
- `Dashboard.md` - Sample dashboard file
- `Company_Handbook.md` - Sample company handbook file
- `watchers/` - Watcher scripts (file system, Gmail, etc.)
- `mcp_servers/` - MCP server implementations
- `requirements.txt` - Python dependencies

### Key Scripts
- `start_mcp_servers.py` - Launches all MCP servers
- `claude_vault_connector.py` - Bridge between Claude and the vault
- `test_claude_vault_connection.py` - Tests the Claude-vault connection
- `orchestrator.py` - Main orchestrator managing all components
- `ralph_wiggum.py` - Ralph Wiggum loop implementation

## Current Progress

### ✅ Gold Tier: Autonomous Employee - COMPLETE

**Last Updated:** February 25, 2026

**Completed Features:**
- 🎉 **Odoo ERP Integration** - Full accounting system with MCP server (port 8005)
- 🎉 **Enhanced CEO Briefing** - Real-time financial data from Odoo
- 🎉 **Invoice Workflow** - Create and manage invoices with approval flow
- 🎉 **Payment Management** - Register and track payments
- 🎉 **Customer Management** - Create and manage customers via Odoo
- 🎉 **Product/Service Catalog** - Manage products and services
- 🎉 **Financial Reporting** - Real-time financial summaries
- 🎉 **Odoo Agent Skill** - YAML-configurable skill for all Odoo operations
- 🎉 **Gold Tier Documentation** - Complete setup and usage guides

**MCP Servers (6 Total):**
1. Filesystem MCP (port 8000)
2. Email MCP (port 8001)
3. LinkedIn MCP (port 8002)
4. Approval MCP (port 8003)
5. WhatsApp MCP (port 8004)
6. **Odoo MCP (port 8005)** ⭐ NEW

**Agent Skills (10+ Total):**
- file_system_watcher
- gmail_watcher
- filesystem_mcp_action
- email_mcp_action
- linkedin_mcp_action
- approval_mcp_action
- **odoo_mcp_action** ⭐ NEW
- payment_action
- whatsapp_action
- banking_action
- reasoning_skill

### ✅ Silver Tier: Functional Assistant - COMPLETE

- ✅ Two or more Watcher scripts (File System + Gmail)
- ✅ Automatically Post on LinkedIn
- ✅ Claude reasoning loop (Plan.md files)
- ✅ Working MCP servers for external actions
- ✅ Human-in-the-loop approval workflow
- ✅ Basic scheduling (APScheduler + Windows Task Scheduler)
- ✅ All AI functionality as Agent Skills

### ✅ Bronze Tier: Foundation - COMPLETE

- ✅ Obsidian vault with Dashboard.md and Company_Handbook.md
- ✅ One working Watcher script
- ✅ Claude Code reading/writing to vault
- ✅ Basic folder structure
- ✅ All AI functionality as Agent Skills

---

## 🎯 What's Next: Platinum Tier

**Platinum Tier** takes the AI Employee to production with:
- **Cloud Deployment** - 24/7 always-on operation
- **Work-Zone Specialization** - Cloud/Local separation
- **Vault Sync** - Git-based or Syncthing synchronization
- **Odoo Cloud** - Deploy Odoo on cloud VM
- **A2A Upgrade** - Direct agent-to-agent messaging

See [TIER_INFO.md](TIER_INFO.md) for Platinum Tier details.