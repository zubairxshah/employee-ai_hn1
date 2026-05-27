"""
Agent Configuration for Platinum Tier
Defines agent roles (CLOUD/LOCAL), domain ownership, and action gating.
"""

import os
from typing import Set


# ==================== AGENT ROLES ====================

CLOUD = "cloud"
LOCAL = "local"

AGENT_ROLE = os.getenv("AGENT_ROLE", LOCAL).lower()
AGENT_ID = os.getenv("AGENT_ID", f"{AGENT_ROLE}-{os.getpid()}")


def is_cloud() -> bool:
    return AGENT_ROLE == CLOUD


def is_local() -> bool:
    return AGENT_ROLE == LOCAL


# ==================== DOMAIN OWNERSHIP ====================
# Which agent owns which task domains

CLOUD_DOMAINS = {"email_triage", "social_drafts", "accounting_read", "health_report"}
LOCAL_DOMAINS = {"approvals", "whatsapp", "payments", "final_send", "dashboard"}

# Actions that are ALWAYS draft-only on Cloud (never executed directly)
CLOUD_DRAFT_ONLY_ACTIONS: Set[str] = {
    # Email
    "send_email",
    "execute_approved_draft",
    # Social
    "create_post",
    "create_tweet",
    "create_instagram_post",
    # Odoo write operations
    "confirm_invoice",
    "register_payment",
}

# Actions allowed on Cloud (read/draft operations)
CLOUD_ALLOWED_ACTIONS: Set[str] = {
    # Email
    "draft",
    "check_draft",
    "capabilities",
    # Social
    "create_draft",
    "check_draft",
    "get_engagement_summary",
    "get_auth_url",
    "exchange_token",
    "refresh_token",
    # Odoo read operations
    "health",
    "get_invoice",
    "get_invoices",
    "get_payments",
    "get_customers",
    "get_products",
    "get_financial_summary",
    "get_customer_statements",
    "get_bank_statements",
    "get_bank_statement_lines",
    "create_invoice",
    "update_invoice",
    "create_customer",
    "create_product",
    "cancel_invoice",
    "reset_invoice_draft",
}

# Local can do everything
LOCAL_ALLOWED_ACTIONS: Set[str] = CLOUD_ALLOWED_ACTIONS | CLOUD_DRAFT_ONLY_ACTIONS


def can_execute_action(action: str) -> bool:
    """
    Check if the current agent role is allowed to execute an action.

    On Cloud: blocks send/post/confirm/payment actions (must go through draft flow).
    On Local: everything is allowed.
    """
    if is_local():
        return True

    # Cloud: block draft-only actions
    if action in CLOUD_DRAFT_ONLY_ACTIONS:
        return False

    # Cloud: allow explicitly allowed actions
    if action in CLOUD_ALLOWED_ACTIONS:
        return True

    # Default: block unknown actions on cloud for safety
    return False


def get_domain_owner(domain: str) -> str:
    """Return which agent role owns a domain."""
    if domain in CLOUD_DOMAINS:
        return CLOUD
    if domain in LOCAL_DOMAINS:
        return LOCAL
    return LOCAL  # Default to local for safety


def get_vault_path() -> str:
    """Get the vault path from environment."""
    return os.getenv("VAULT_PATH", r"D:\prompteng\AI_Employee_Vault")
