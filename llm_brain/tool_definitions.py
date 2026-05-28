"""
Gemini function declarations for every MCP tool the brain can call.

Naming: <service>__<endpoint>. The tool_executor splits on `__` and routes to
the matching MCP server. Cloud/Local gating is enforced at runtime by
agent_config.can_execute_action() — drafts/reads always allowed, sends/posts/
financial-confirms blocked on cloud.

Adding a new endpoint: append a FunctionDeclaration to the right section, then
ensure the action name matches the Flask @app.route in mcp_servers/. GET
endpoints must also be added to _GET_ACTIONS in tool_executor.py.
"""

from google.genai import types


# ============================================================
# Filesystem MCP (8000) — read/write inside the vault
# ============================================================

FILESYSTEM_TOOLS = [
    types.FunctionDeclaration(
        name="filesystem__read_file",
        description="Read the contents of a file from the vault.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path within the vault."},
            },
            "required": ["path"],
        },
    ),
    types.FunctionDeclaration(
        name="filesystem__write_file",
        description="Write content to a file. Overwrites if it exists.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
    ),
    types.FunctionDeclaration(
        name="filesystem__list_files",
        description="List files in a vault directory.",
        parameters={
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    ),
    # NOTE: filesystem__move_file is intentionally NOT exposed.
    # The MCP's /move_file route goes through SecureActionExecutor.file_operation()
    # which is a stub (secure_action_executor.py:210) — it returns success without
    # actually moving the file. Task lifecycle moves (Needs_Action → Done) should
    # be handled by claim_manager.os.rename() in task_queue.py, not by the brain.
]


# ============================================================
# Email MCP (8001) — Gmail SMTP send + draft flow
# ============================================================

EMAIL_TOOLS = [
    types.FunctionDeclaration(
        name="email__send_email",
        description="Send an email IMMEDIATELY via Gmail SMTP. LOCAL role only — use email__send_draft on CLOUD.",
        parameters={
            "type": "object",
            "properties": {
                "to": {"type": "string"},
                "subject": {"type": "string"},
                "body": {"type": "string"},
                "html": {"type": "boolean"},
            },
            "required": ["to", "subject", "body"],
        },
    ),
    types.FunctionDeclaration(
        name="email__send_draft",
        description="Create an email draft in Pending_Approval/Email_Drafts/ for human approval. Safe on CLOUD.",
        parameters={
            "type": "object",
            "properties": {
                "to": {"type": "string"},
                "subject": {"type": "string"},
                "body": {"type": "string"},
                "html": {"type": "boolean"},
            },
            "required": ["to", "subject", "body"],
        },
    ),
    types.FunctionDeclaration(
        name="email__check_draft_status",
        description="Check whether an email draft has been approved, rejected, or is still pending.",
        parameters={
            "type": "object",
            "properties": {"filepath": {"type": "string"}},
            "required": ["filepath"],
        },
    ),
    types.FunctionDeclaration(
        name="email__execute_approved_draft",
        description="Send a previously-approved email draft. The draft file must be in Approved/Email_Drafts/.",
        parameters={
            "type": "object",
            "properties": {"filepath": {"type": "string"}},
            "required": ["filepath"],
        },
    ),
]


# ============================================================
# LinkedIn MCP (8002)
# ============================================================

LINKEDIN_TOOLS = [
    types.FunctionDeclaration(
        name="linkedin__create_post",
        description="Publish a LinkedIn post immediately. LOCAL only — use create_draft on CLOUD.",
        parameters={
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "visibility": {"type": "string", "description": "'PUBLIC' (default) or 'CONNECTIONS'."},
                "images": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of vault-relative image paths.",
                },
            },
            "required": ["text"],
        },
    ),
    types.FunctionDeclaration(
        name="linkedin__create_draft",
        description="Save a LinkedIn post as a draft in Pending_Approval/Social_Drafts/.",
        parameters={
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "visibility": {"type": "string"},
            },
            "required": ["text"],
        },
    ),
    types.FunctionDeclaration(
        name="linkedin__check_draft_status",
        description="Check whether a LinkedIn draft is approved/rejected/pending.",
        parameters={
            "type": "object",
            "properties": {"filename": {"type": "string"}},
            "required": ["filename"],
        },
    ),
    types.FunctionDeclaration(
        name="linkedin__execute_approved_draft",
        description="Publish an approved LinkedIn draft.",
        parameters={
            "type": "object",
            "properties": {"filename": {"type": "string"}},
            "required": ["filename"],
        },
    ),
    types.FunctionDeclaration(
        name="linkedin__get_messages",
        description="Fetch recent LinkedIn inbox messages. Read-only.",
        parameters={"type": "object", "properties": {}},
    ),
]


# ============================================================
# Approval MCP (8003) — human-in-the-loop for high-stakes actions
# ============================================================

APPROVAL_TOOLS = [
    types.FunctionDeclaration(
        name="approval__request_approval",
        description="Request human approval for an action above the auto-approve threshold. Returns a request_id.",
        parameters={
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "Short label, e.g. 'send_invoice', 'register_payment'."},
                "amount": {"type": "number"},
                "recipient": {"type": "string"},
                "reason": {"type": "string", "description": "Why this action is being requested."},
            },
            "required": ["action", "reason"],
        },
    ),
    types.FunctionDeclaration(
        name="approval__check_approval",
        description="Poll the status of a previously-requested approval (returns approved/rejected/pending).",
        parameters={
            "type": "object",
            "properties": {"request_id": {"type": "string"}},
            "required": ["request_id"],
        },
    ),
    types.FunctionDeclaration(
        name="approval__approve_action",
        description="Mark an approval request as approved. Typically called by the LOCAL agent on behalf of the human.",
        parameters={
            "type": "object",
            "properties": {"request_id": {"type": "string"}},
            "required": ["request_id"],
        },
    ),
    types.FunctionDeclaration(
        name="approval__reject_action",
        description="Mark an approval request as rejected.",
        parameters={
            "type": "object",
            "properties": {"request_id": {"type": "string"}},
            "required": ["request_id"],
        },
    ),
    types.FunctionDeclaration(
        name="approval__list_pending_approvals",
        description="List all approval requests still awaiting a decision.",
        parameters={"type": "object", "properties": {}},
    ),
]


# ============================================================
# WhatsApp MCP (8004) — notifications + custom messages
# ============================================================

WHATSAPP_TOOLS = [
    types.FunctionDeclaration(
        name="whatsapp__send_notification",
        description="Send a structured approval notification to the configured WhatsApp number. LOCAL only.",
        parameters={
            "type": "object",
            "properties": {
                "action": {"type": "string"},
                "amount": {"type": "string"},
                "recipient": {"type": "string"},
                "reason": {"type": "string"},
                "phone": {"type": "string", "description": "Override target number; defaults to WHATSAPP_NOTIFICATION_PHONE."},
            },
            "required": ["action"],
        },
    ),
    types.FunctionDeclaration(
        name="whatsapp__send_custom_message",
        description="Send an arbitrary text message via WhatsApp. LOCAL only.",
        parameters={
            "type": "object",
            "properties": {
                "phone": {"type": "string"},
                "message": {"type": "string"},
            },
            "required": ["phone", "message"],
        },
    ),
]


# ============================================================
# Odoo MCP (8005) — ERP / accounting
# ============================================================

ODOO_TOOLS = [
    types.FunctionDeclaration(
        name="odoo__create_invoice",
        description="Create a draft invoice in Odoo. Always safe — invoice stays in draft until confirm_invoice is called.",
        parameters={
            "type": "object",
            "properties": {
                "partner_id": {"type": "integer", "description": "Odoo customer id."},
                "lines": {
                    "type": "array",
                    "description": "Invoice lines, each {product_id, quantity, price_unit, name}.",
                    "items": {"type": "object"},
                },
                "invoice_date": {"type": "string", "description": "YYYY-MM-DD. Defaults to today."},
                "invoice_date_due": {"type": "string"},
                "narration": {"type": "string"},
            },
            "required": ["partner_id", "lines"],
        },
    ),
    types.FunctionDeclaration(
        name="odoo__update_invoice",
        description="Update fields on an existing draft invoice.",
        parameters={
            "type": "object",
            "properties": {
                "invoice_id": {"type": "integer"},
                "values": {"type": "object", "description": "Field updates, e.g. {'narration': '...'}."},
            },
            "required": ["invoice_id", "values"],
        },
    ),
    types.FunctionDeclaration(
        name="odoo__confirm_invoice",
        description="Confirm/post an invoice (moves from draft to posted). LOCAL only — high-stakes.",
        parameters={
            "type": "object",
            "properties": {"invoice_id": {"type": "integer"}},
            "required": ["invoice_id"],
        },
    ),
    types.FunctionDeclaration(
        name="odoo__cancel_invoice",
        description="Cancel an invoice.",
        parameters={
            "type": "object",
            "properties": {"invoice_id": {"type": "integer"}},
            "required": ["invoice_id"],
        },
    ),
    types.FunctionDeclaration(
        name="odoo__reset_invoice_draft",
        description="Reset a posted/cancelled invoice back to draft.",
        parameters={
            "type": "object",
            "properties": {"invoice_id": {"type": "integer"}},
            "required": ["invoice_id"],
        },
    ),
    types.FunctionDeclaration(
        name="odoo__get_invoices",
        description="List invoices. Filter by partner, type, state, or ref. Use the 'ref' filter (exact match on Customer Reference) to look up invoices by their internal identifier like 'INV-002' — Odoo's auto-generated 'name' is a sequence like 'INV/2026/00009', not your internal ID.",
        parameters={
            "type": "object",
            "properties": {
                "partner_id": {"type": "integer"},
                "move_type": {"type": "string", "description": "'out_invoice' (customer) or 'in_invoice' (vendor)."},
                "state": {"type": "string", "description": "'draft' | 'posted' | 'cancel'."},
                "ref": {"type": "string", "description": "Customer Reference, exact match (e.g. 'INV-002')."},
                "limit": {"type": "integer"},
            },
        },
    ),
    types.FunctionDeclaration(
        name="odoo__get_invoice",
        description="Fetch a single invoice by id.",
        parameters={
            "type": "object",
            "properties": {"invoice_id": {"type": "integer"}},
            "required": ["invoice_id"],
        },
    ),
    types.FunctionDeclaration(
        name="odoo__register_payment",
        description="Register a payment against an invoice. LOCAL only — high-stakes.",
        parameters={
            "type": "object",
            "properties": {
                "invoice_id": {"type": "integer"},
                "amount": {"type": "number"},
                "payment_date": {"type": "string", "description": "YYYY-MM-DD."},
                "payment_method": {"type": "string"},
                "journal_id": {"type": "integer"},
            },
            "required": ["invoice_id", "amount"],
        },
    ),
    types.FunctionDeclaration(
        name="odoo__get_payments",
        description="List payments. Filter by partner and state.",
        parameters={
            "type": "object",
            "properties": {
                "partner_id": {"type": "integer"},
                "state": {"type": "string"},
                "limit": {"type": "integer"},
            },
        },
    ),
    types.FunctionDeclaration(
        name="odoo__get_customers",
        description="List/search Odoo customers (partners).",
        parameters={
            "type": "object",
            "properties": {
                "search": {"type": "string", "description": "Substring to match on name."},
                "limit": {"type": "integer"},
            },
        },
    ),
    types.FunctionDeclaration(
        name="odoo__create_customer",
        description="Create a new customer record.",
        parameters={
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "email": {"type": "string"},
                "phone": {"type": "string"},
                "country_id": {"type": "integer"},
            },
            "required": ["name"],
        },
    ),
    types.FunctionDeclaration(
        name="odoo__get_products",
        description="List/search products.",
        parameters={
            "type": "object",
            "properties": {
                "type": {"type": "string", "description": "'product' | 'service' | 'consu'."},
                "search": {"type": "string"},
                "limit": {"type": "integer"},
            },
        },
    ),
    types.FunctionDeclaration(
        name="odoo__create_product",
        description="Create a new product.",
        parameters={
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "type": {"type": "string"},
                "list_price": {"type": "number"},
                "description": {"type": "string"},
                "default_code": {"type": "string"},
            },
            "required": ["name", "type", "list_price"],
        },
    ),
    types.FunctionDeclaration(
        name="odoo__get_financial_summary",
        description="Get revenue, expenses, and net for a date range. Defaults to current month.",
        parameters={
            "type": "object",
            "properties": {
                "date_from": {"type": "string"},
                "date_to": {"type": "string"},
            },
        },
    ),
    types.FunctionDeclaration(
        name="odoo__get_customer_statements",
        description="Get an account statement for one customer over a date range.",
        parameters={
            "type": "object",
            "properties": {
                "partner_id": {"type": "integer"},
                "date_from": {"type": "string"},
                "date_to": {"type": "string"},
            },
            "required": ["partner_id"],
        },
    ),
    types.FunctionDeclaration(
        name="odoo__get_bank_statements",
        description="List bank statements. Filter by journal/state.",
        parameters={
            "type": "object",
            "properties": {
                "journal_id": {"type": "integer"},
                "state": {"type": "string"},
                "limit": {"type": "integer"},
            },
        },
    ),
    types.FunctionDeclaration(
        name="odoo__get_bank_statement_lines",
        description="List individual lines (transactions) from a bank statement.",
        parameters={
            "type": "object",
            "properties": {
                "statement_id": {"type": "integer"},
                "limit": {"type": "integer"},
            },
        },
    ),
]


# ============================================================
# Facebook MCP (8006) — Facebook + Instagram
# ============================================================

FACEBOOK_TOOLS = [
    types.FunctionDeclaration(
        name="facebook__create_post",
        description="Publish a Facebook page post immediately. LOCAL only — use create_draft on CLOUD.",
        parameters={
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Post text. 'text' is also accepted."},
                "image_url": {"type": "string"},
            },
            "required": ["message"],
        },
    ),
    types.FunctionDeclaration(
        name="facebook__create_instagram_post",
        description="Publish an Instagram post immediately. Requires image_url. LOCAL only.",
        parameters={
            "type": "object",
            "properties": {
                "caption": {"type": "string"},
                "image_url": {"type": "string"},
            },
            "required": ["caption", "image_url"],
        },
    ),
    types.FunctionDeclaration(
        name="facebook__create_draft",
        description="Save a Facebook/Instagram post as a draft.",
        parameters={
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "platform": {"type": "string", "description": "'facebook' (default) or 'instagram'."},
                "image_url": {"type": "string"},
            },
            "required": ["text"],
        },
    ),
    types.FunctionDeclaration(
        name="facebook__check_draft_status",
        description="Check approval status of a Facebook/Instagram draft.",
        parameters={
            "type": "object",
            "properties": {"filename": {"type": "string"}},
            "required": ["filename"],
        },
    ),
    types.FunctionDeclaration(
        name="facebook__execute_approved_draft",
        description="Publish an approved Facebook/Instagram draft.",
        parameters={
            "type": "object",
            "properties": {"filename": {"type": "string"}},
            "required": ["filename"],
        },
    ),
    types.FunctionDeclaration(
        name="facebook__get_engagement_summary",
        description="Get recent engagement metrics (likes, comments, reach).",
        parameters={"type": "object", "properties": {}},
    ),
]


# ============================================================
# Twitter / X MCP (8007)
# ============================================================

TWITTER_TOOLS = [
    types.FunctionDeclaration(
        name="twitter__create_tweet",
        description="Post a tweet immediately. LOCAL only — use create_draft on CLOUD.",
        parameters={
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    ),
    types.FunctionDeclaration(
        name="twitter__create_draft",
        description="Save a tweet as a draft for human approval.",
        parameters={
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    ),
    types.FunctionDeclaration(
        name="twitter__check_draft_status",
        description="Check approval status of a tweet draft.",
        parameters={
            "type": "object",
            "properties": {"filename": {"type": "string"}},
            "required": ["filename"],
        },
    ),
    types.FunctionDeclaration(
        name="twitter__execute_approved_draft",
        description="Post an approved tweet draft.",
        parameters={
            "type": "object",
            "properties": {"filename": {"type": "string"}},
            "required": ["filename"],
        },
    ),
    types.FunctionDeclaration(
        name="twitter__get_engagement_summary",
        description="Get recent tweet engagement metrics.",
        parameters={"type": "object", "properties": {}},
    ),
]


# ============================================================
# Aggregator
# ============================================================

ALL_TOOL_DECLARATIONS = (
    FILESYSTEM_TOOLS
    + EMAIL_TOOLS
    + LINKEDIN_TOOLS
    + APPROVAL_TOOLS
    + WHATSAPP_TOOLS
    + ODOO_TOOLS
    + FACEBOOK_TOOLS
    + TWITTER_TOOLS
)


def build_tools() -> list:
    """Return a list[Tool] ready to pass to GenerateContentConfig(tools=...) — Gemini format."""
    return [types.Tool(function_declarations=ALL_TOOL_DECLARATIONS)]


def tool_names() -> list:
    return [fd.name for fd in ALL_TOOL_DECLARATIONS]


def _lowercase_schema_types(node):
    """Recursively lowercase JSON-Schema type values (Gemini emits OBJECT/STRING; OpenAI wants object/string)."""
    if isinstance(node, dict):
        return {k: (v.lower() if k == "type" and isinstance(v, str) else _lowercase_schema_types(v))
                for k, v in node.items()}
    if isinstance(node, list):
        return [_lowercase_schema_types(item) for item in node]
    return node


def build_openai_tools() -> list:
    """Return tool list in OpenAI / OpenRouter chat-completions format."""
    out = []
    for fd in ALL_TOOL_DECLARATIONS:
        dumped = fd.model_dump(exclude_none=True)
        params = _lowercase_schema_types(dumped.get("parameters", {"type": "object", "properties": {}}))
        out.append({
            "type": "function",
            "function": {
                "name": dumped["name"],
                "description": dumped.get("description", ""),
                "parameters": params,
            },
        })
    return out
