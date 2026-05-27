"""Settings for the LLM Brain — provider, rate limits, MCP endpoints, role gating."""

import os
from pathlib import Path


# ==================== Provider ====================
# LLM_BRAIN_PROVIDER selects which backend to use: "gemini" or "openrouter".

PROVIDER = os.getenv("LLM_BRAIN_PROVIDER", "gemini").lower()

# Gemini (google-genai) settings
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("LLM_BRAIN_MODEL", "gemini-2.5-flash")

# OpenRouter (openai-compatible) settings
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_MODEL = os.getenv("LLM_BRAIN_OPENROUTER_MODEL", "deepseek/deepseek-v4-flash:free")

# Resolved model name for the active provider (read after PROVIDER is set)
MODEL_NAME = OPENROUTER_MODEL if PROVIDER == "openrouter" else GEMINI_MODEL


# ==================== Agentic loop limits ====================

MAX_TURNS_PER_TASK = int(os.getenv("LLM_BRAIN_MAX_TURNS", "15"))
MAX_TASKS_PER_HOUR = int(os.getenv("LLM_BRAIN_MAX_TASKS_HOUR", "30"))


# ==================== MCP server endpoints ====================

MCP_BASE_URLS = {
    "filesystem": os.getenv("MCP_FILESYSTEM_URL", "http://localhost:8000"),
    "email": os.getenv("MCP_EMAIL_URL", "http://localhost:8001"),
    "linkedin": os.getenv("MCP_LINKEDIN_URL", "http://localhost:8002"),
    "approval": os.getenv("MCP_APPROVAL_URL", "http://localhost:8003"),
    "whatsapp": os.getenv("MCP_WHATSAPP_URL", "http://localhost:8004"),
    "odoo": os.getenv("MCP_ODOO_URL", "http://localhost:8005"),
    "facebook": os.getenv("MCP_FACEBOOK_URL", "http://localhost:8006"),
    "twitter": os.getenv("MCP_TWITTER_URL", "http://localhost:8007"),
}


# ==================== Approval thresholds (dollar amounts) ====================

AUTO_APPROVE_BELOW = 100
REQUEST_APPROVAL_BELOW = 500


# ==================== Vault paths ====================

VAULT_PATH = Path(os.getenv("VAULT_PATH", r"D:\prompteng\AI_Employee_Vault"))


def validate() -> None:
    """Raise if required config is missing for the selected provider."""
    if PROVIDER == "gemini":
        if not GEMINI_API_KEY:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Get a free key at "
                "https://aistudio.google.com/apikey and add to .env"
            )
    elif PROVIDER == "openrouter":
        if not OPENROUTER_API_KEY:
            raise RuntimeError(
                "OPENROUTER_API_KEY is not set. Get a key at "
                "https://openrouter.ai/keys and add to .env"
            )
    else:
        raise RuntimeError(f"Unknown LLM_BRAIN_PROVIDER: {PROVIDER} (expected 'gemini' or 'openrouter')")
