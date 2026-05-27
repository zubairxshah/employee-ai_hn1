# LLM Brain Orchestration Guide

## Overview

The LLM Brain replaces the hardcoded orchestrators (`cloud_orchestrator.py`, `local_orchestrator.py`) with an intelligent, LLM-controlled agentic loop. Instead of template-based routing, **Claude API reasons about each task**, generates custom content, decides which tools to call, and handles approval workflows autonomously.

### What Changes

| Before (Hardcoded) | After (LLM Brain) |
|---|---|
| Template-based email drafts | Claude writes contextual, personalized responses |
| Fixed `if action == "send_email"` routing | Claude decides which tools to call based on task context |
| Keyword-based task classification | Claude understands task intent naturally |
| No content generation | Custom social posts, email replies, invoice summaries |
| Manual multi-step coordination | Claude handles full workflows end-to-end |

### What Stays the Same

- All 8 MCP servers (unchanged HTTP endpoints)
- All watchers (Gmail, LinkedIn, WhatsApp, Filesystem)
- Vault directory structure (Needs_Action, Pending_Approval, Done, etc.)
- Cloud/Local safety gating (cloud can only draft, local can execute)
- Approval workflow (file-based in Obsidian)

---

## Architecture

```
Watchers (unchanged)             Vault Filesystem
  Gmail Watcher      ─┐           ┌──────────────┐
  LinkedIn Watcher   ─┤  write──> │ Needs_Action/  │
  File System Watcher─┤           └──────┬───────┘
  WhatsApp Watcher   ─┘                  │ scan
                                         v
                               ┌───────────────────┐
                               │   Task Queue       │
                               │  (priority-based)  │
                               └─────────┬─────────┘
                                         │ dequeue
                                         v
                               ┌───────────────────┐
                               │   LLM Brain        │
                               │  (Claude API with  │
                               │   tool_use calls)  │
                               └─────────┬─────────┘
                                         │ tool calls
                                         v
                               ┌───────────────────┐
                               │  Tool Executor     │
                               │  (HTTP bridge)     │
                               └─────────┬─────────┘
                                         │ HTTP POST/GET
                    ┌────────┬───────┬───┴───┬────────┬────────┐
                    │Email   │Odoo   │Social │Approve │WhatsApp│
                    │:8001   │:8005  │:8002  │:8003   │:8004   │
                    │        │       │:8006  │        │        │
                    │        │       │:8007  │        │        │
                    └────────┴───────┴───────┴────────┴────────┘
```

### How It Works

1. **Watchers** detect incoming signals (emails, messages, file drops) and create `.md` task files in `Needs_Action/`
2. **Task Queue** scans the vault, parses tasks, and prioritizes them
3. **LLM Brain** picks the highest-priority task and starts a Claude API conversation
4. **Claude reasons** about the task, decides what to do, and calls tools (MCP endpoints)
5. **Tool Executor** translates Claude's tool calls into HTTP requests to MCP servers
6. Results feed back to Claude for the next reasoning step
7. When approval is needed, the task is **parked** with its conversation history
8. After approval, the conversation **resumes** from where it left off

---

## Package Structure

```
llm_brain/
  __init__.py              # Package init
  config.py                # All customizable settings (see Admin Configuration below)
  brain.py                 # Core agentic loop
  tool_definitions.py      # Claude API tool schemas for all MCP endpoints
  tool_executor.py         # HTTP bridge between Claude and MCP servers
  task_queue.py            # Task ingestion, parsing, priority queue
  system_prompt.py         # System prompt builder
  approval_handler.py      # Approval parking and resumption
```

### Entry Points

```bash
# Run as Local Agent (full execution rights)
set AGENT_ROLE=local
python run_brain_local.py

# Run as Cloud Agent (draft-only, no send/post/pay)
set AGENT_ROLE=cloud
python run_brain_cloud.py
```

---

## Admin Configuration

All customizable settings are in `llm_brain/config.py`. Admins can tune the LLM behavior without touching the core logic.

### Model Settings

```python
# Which Claude model to use for the agentic loop
LLM_MODEL = "claude-sonnet-4-20250514"
# Options:
#   "claude-sonnet-4-20250514"  - Fast, cost-effective (recommended for production)
#   "claude-opus-4-20250514"    - Most capable, 5x more expensive (for complex reasoning)

# Maximum tokens per response
LLM_MAX_TOKENS = 4096
```

### Rate Limits & Cost Control

```python
# Maximum Claude API calls per single task (prevents runaway loops)
MAX_API_CALLS_PER_TASK = 15

# Maximum tasks processed per hour (cost control)
MAX_TASKS_PER_HOUR = 30

# Polling interval in seconds between task scans
POLL_INTERVAL = 15
```

### Approval Thresholds

These control when the LLM must request human approval before executing an action.

```python
APPROVAL_THRESHOLDS = {
    # Payments and invoices
    "payment": {
        "auto_approve_below": 100,       # Under $100: execute without asking
        "request_approval_below": 500,    # $100-$500: request approval, notify admin
        "always_require_above": 500,      # Over $500: always require approval
    },

    # Email sending
    "email": {
        "auto_approve_below": 50,         # Simple responses: auto-approve
        "bulk_always_approve": True,      # Bulk emails always need approval
        "new_contacts_approve": True,     # First email to new contact needs approval
    },

    # Social media posting
    "social_media": {
        "always_require_approval": True,  # All social posts need approval by default
        # Set to False to let LLM post autonomously
    },

    # Order processing
    "orders": {
        "auto_process_below": 100,        # Small orders: process automatically
        "notify_above": 250,              # Notify admin for orders above this
        "require_approval_above": 500,    # Require approval for large orders
    },
}
```

### Content Generation Rules

Control how the LLM generates content for different channels.

```python
CONTENT_RULES = {
    "email": {
        "tone": "professional",           # professional, friendly, formal, casual
        "max_length": 500,                # Maximum words per email
        "include_signature": True,
        "signature": "Best regards,\nYour Company Name",
        "language": "English",
    },

    "social_media": {
        "brand_voice": "innovative and approachable",
        "include_hashtags": True,
        "max_hashtags": 5,
        "platforms_enabled": ["linkedin", "facebook", "twitter"],
        "twitter_max_chars": 280,
    },

    "notifications": {
        "whatsapp_enabled": True,         # Send WhatsApp alerts for approvals
        "notification_phone": None,       # Uses WHATSAPP_NOTIFICATION_PHONE from .env
        "notify_on_completion": True,     # Notify when tasks complete
        "notify_on_error": True,          # Notify when tasks fail
    },
}
```

### Task Priority Configuration

Control which tasks get processed first.

```python
TASK_PRIORITIES = {
    "whatsapp": 1,       # Urgent human messages - process first
    "accounting": 2,     # Financial tasks - high priority
    "email": 3,          # Email responses - medium priority
    "social": 4,         # Social media - can wait
    "file_drop": 5,      # File processing - lowest priority
    "general": 6,
}
```

### Custom Business Rules

Add your own rules that the LLM will follow. These are injected into the system prompt.

```python
CUSTOM_RULES = [
    "Always CC manager@company.com on invoices above $1000",
    "Do not respond to spam or promotional emails",
    "LinkedIn posts should be published between 9 AM and 5 PM",
    "For new customer inquiries, always create a lead in Odoo before responding",
    "Never disclose pricing without checking the latest product catalog in Odoo",
]
```

### Company Handbook

The LLM reads `Company_Handbook.md` in the project root for business context. Update this file to change how the LLM understands your company's policies, products, and procedures.

---

## Approval Workflow

### How Approvals Work

1. LLM encounters a task requiring approval (based on thresholds above)
2. LLM calls `approval__request_approval` with action details
3. LLM calls `whatsapp__send_notification` to alert the admin
4. Task is **parked**: conversation history saved to `Pending_Approval/{task_id}_context.json`
5. LLM stops processing this task and moves to the next one
6. Admin reviews in Obsidian and moves the file from `Pending_Approval/` to `Approved/` or `Rejected/`
7. Next cycle: LLM Brain detects the approval, loads saved conversation, and **resumes** processing

### What Gets Parked

The full conversation (task description, LLM's reasoning, all tool calls and results so far) is saved. When resumed, the LLM has complete context about what it was doing and why.

### Approval Notification Example

When the LLM requests approval, the admin receives a WhatsApp message like:

```
Approval Needed:
Action: Confirm Invoice #1234
Amount: $350.00
Customer: Acme Corporation
Reason: Consulting services - March 2026

Review in Obsidian vault -> Pending_Approval/
```

---

## Example Workflows

### 1. Custom Email Response

```
Input:  Email from client asking about project status
LLM:    1. Reads email content and context
        2. Checks Odoo for related invoices/orders
        3. Drafts a personalized reply with project details
        4. Sends email (or creates draft if approval needed)
```

### 2. Order Processing

```
Input:  Email with purchase order for $2,500
LLM:    1. Parses order details from email
        2. Looks up customer in Odoo (creates if new)
        3. Creates invoice with line items
        4. Amount > $500 -> requests approval + WhatsApp notification
        5. [Parked - waiting for approval]
        6. [Resumed after approval]
        7. Confirms invoice in Odoo
        8. Sends confirmation email to customer
        9. Moves task to Done
```

### 3. Marketing Campaign Post

```
Input:  Task file requesting LinkedIn post about new product
LLM:    1. Reads product details from Odoo (get_products)
        2. Generates engaging post with brand voice
        3. Creates draft for approval
        4. [Parked - waiting for approval]
        5. [Resumed after approval]
        6. Posts to LinkedIn
        7. Optionally cross-posts to Facebook/Twitter
```

### 4. Financial Report

```
Input:  Task requesting weekly financial summary
LLM:    1. Calls odoo__get_financial_summary for date range
        2. Calls odoo__get_invoices for recent activity
        3. Calls odoo__get_payments for payment status
        4. Generates summary report
        5. Writes report to vault via filesystem__write_file
        6. Sends summary email to admin
```

---

## Safety & Security

### Cloud/Local Gating

- **Cloud agent** can only: read data, create drafts, check statuses
- **Cloud agent** CANNOT: send emails, post to social media, confirm invoices, register payments
- **Local agent** can do everything
- This is enforced at two levels: tool schema filtering AND runtime execution checks

### Action Blocking

Even if the LLM generates a tool call it shouldn't, the Tool Executor checks `agent_config.can_execute_action()` and blocks it with an error response back to the LLM.

### Sensitive Data

- API keys and credentials stay in `.env` (never exposed to LLM)
- The LLM sees task content only, not raw credentials
- `security_config.py` defines `SENSITIVE_CREDENTIALS` that are blocked from cloud

---

## Monitoring & Logs

- All LLM Brain activity logged via `production_utils.get_structured_logger()`
- Each task processing creates a log trail: task claimed -> API calls made -> tools executed -> result
- Conversation histories for approval-parked tasks are saved as JSON files
- Dashboard updates written to `Updates/` directory

---

## Customization Checklist

When setting up the LLM Brain for a new deployment:

1. [ ] Set `ANTHROPIC_API_KEY` in `.env`
2. [ ] Review `llm_brain/config.py` approval thresholds
3. [ ] Update `Company_Handbook.md` with company-specific rules
4. [ ] Set content generation rules (tone, signature, brand voice)
5. [ ] Configure `CUSTOM_RULES` for business-specific behavior
6. [ ] Adjust `MAX_TASKS_PER_HOUR` for cost control
7. [ ] Choose model (`sonnet` for cost, `opus` for capability)
8. [ ] Test with a few sample tasks before enabling full automation

---

## Costs Estimate

| Scenario | Tokens/Task | Cost/Task (Sonnet) | Monthly (30 tasks/day) |
|---|---|---|---|
| Simple email reply | ~3,000 | ~$0.01 | ~$9 |
| Multi-step order processing | ~15,000 | ~$0.05 | ~$45 |
| Social media campaign | ~8,000 | ~$0.03 | ~$27 |
| Mixed workload (avg) | ~8,000 | ~$0.03 | ~$27 |

*Based on Claude Sonnet pricing. Opus would be approximately 5x these costs.*
