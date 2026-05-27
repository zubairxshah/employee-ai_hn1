# Personal AI Employee Development Tiers

## Bronze Tier: Foundation (Minimum Viable Deliverable)
**Estimated time:** 8-12 hours

### Requirements:
- Obsidian vault with Dashboard.md and Company_Handbook.md
- One working Watcher script (Gmail OR file system monitoring)
- Claude Code successfully reading from and writing to the vault
- Basic folder structure: /Inbox, /Needs_Action, /Done
- All AI functionality should be implemented as Agent Skills

---

## Silver Tier: Functional Assistant
**Estimated time:** 20-30 hours

### Requirements:
- All Bronze requirements plus:
- Two or more Watcher scripts (e.g., Gmail + Whatsapp + LinkedIn)
- Automatically Post on LinkedIn about business to generate sales
- Claude reasoning loop that creates Plan.md files
- One working MCP server for external action (e.g., sending emails)
- Human-in-the-loop approval workflow for sensitive actions
- Basic scheduling via cron or Task Scheduler
- All AI functionality should be implemented as Agent Skills

---

## Gold Tier: Autonomous Employee
**Estimated time:** 40+ hours

### Requirements:
- All Silver requirements plus:
- Full cross-domain integration (Personal + Business)
- Create an accounting system for your business in Odoo Community (self-hosted, local) and integrate it via an MCP server using Odoo's JSON-RPC APIs (Odoo 19+)
- Integrate Facebook and Instagram and post messages and generate summary
- Integrate Twitter (X) and post messages and generate summary
- Multiple MCP servers for different action types
- Weekly Business and Accounting Audit with CEO Briefing generation
- Error recovery and graceful degradation
- Comprehensive audit logging
- Ralph Wiggum loop for autonomous multi-step task completion (see Section 2D)
- Documentation of your architecture and lessons learned
- All AI functionality should be implemented as Agent Skills

---

## Platinum Tier: Always-On Cloud + Local Executive (Production-ish AI Employee)
**Estimated time:** 60+ hours

### Requirements:
- All Gold requirements plus:
- Run the AI Employee on Cloud 24/7 (always-on watchers + orchestrator + health monitoring). You can deploy a Cloud VM (Oracle/AWS/etc.) - Oracle Cloud Free VMs can be used for this (subject to limits/availability).
- Work-Zone Specialization (domain ownership):
  - Cloud owns: Email triage + draft replies + social post drafts/scheduling (draft-only; requires Local approval before send/post)
  - Local owns: approvals, WhatsApp session, payments/banking, and final "send/post" actions
- Delegation via Synced Vault (Phase 1)
- Agents communicate by writing files into:
  - /Needs_Action/<domain>/, /Plans/<domain>/, /Pending_Approval/<domain>/
- Prevent double-work using:
  - /In_Progress/<agent>/ claim-by-move rule
  - single-writer rule for Dashboard.md (Local)
- Cloud writes updates to /Updates/ (or /Signals/), and Local merges them into Dashboard.md.
- For Vault sync (Phase 1) use Git (recommended) or Syncthing.
- Claim-by-move rule: first agent to move an item from /Needs_Action to /In_Progress/<agent>/ owns it; other agents must ignore it.
- Security rule: Vault sync includes only markdown/state. Secrets never sync (.env, tokens, WhatsApp sessions, banking creds). So Cloud never stores or uses WhatsApp sessions, banking credentials, or payment tokens.
- Deploy Odoo Community on a Cloud VM (24/7) with HTTPS, backups, and health monitoring; integrate Cloud Agent with Odoo via MCP for draft-only accounting actions and Local approval for posting invoices/payments.
- Optional A2A Upgrade (Phase 2): Replace some file handoffs with direct A2A messages later, while keeping the vault as the audit record

### Platinum Demo (minimum passing gate):
Email arrives while Local is offline → Cloud drafts reply + writes approval file → when Local returns, user approves → Local executes send via MCP → logs → moves task to /Done.