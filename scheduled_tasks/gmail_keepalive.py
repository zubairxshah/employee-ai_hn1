"""
Gmail OAuth Keepalive

Google revokes refresh tokens that go unused for 6 months, and deletes OAuth
clients with no recorded usage over the same window. In 2026 this project sat
idle from February to September and lost both -- the token had to be re-authed
by hand and the client was flagged for deletion in Cloud Console.

This task makes a real Gmail API call on a schedule so neither clock ever runs
out. It also refreshes and re-persists the token, so the stored credentials
stay current between real workloads.

Run manually:  python scheduled_tasks/gmail_keepalive.py
Scheduled by:  setup_gmail_keepalive.py (Windows Task Scheduler, weekly)

Exits 0 on success, 1 on failure, so Task Scheduler records a failed run.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

VAULT_PATH = Path(os.getenv("VAULT_PATH", r"D:\prompteng\AI_Employee_Vault"))
LOG_FILE = VAULT_PATH / "Scheduled_Tasks" / "gmail_keepalive.jsonl"
FALLBACK_LOG_FILE = PROJECT_ROOT / "logs" / "gmail_keepalive.jsonl"


def write_log(entry):
    """Append one JSON line, falling back to the project dir if the vault is gone"""
    entry["timestamp"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    line = json.dumps(entry) + "\n"

    for target in (LOG_FILE, FALLBACK_LOG_FILE):
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "a", encoding="utf-8") as f:
                f.write(line)
            return target
        except OSError:
            continue

    # Logging must never be the reason the keepalive fails
    return None


def run_keepalive():
    """Refresh credentials and make a real Gmail API call. Returns (ok, detail)"""
    # Imported here so an import failure is caught and logged like any other
    from mcp_servers.email_mcp import get_gmail_credentials, get_gmail_service

    creds = get_gmail_credentials()
    service = get_gmail_service()

    # getProfile is the cheapest call that still counts as client usage
    profile = service.users().getProfile(userId="me").execute()

    return {
        "address": profile.get("emailAddress"),
        "messages_total": profile.get("messagesTotal"),
        "token_expiry": creds.expiry.isoformat() if creds.expiry else None,
        "scopes": sorted(creds.scopes or []),
    }


def main():
    print("=" * 60)
    print("  Gmail OAuth Keepalive")
    print("=" * 60)

    try:
        detail = run_keepalive()
    except Exception as e:
        # Any failure here means the token or client needs human attention
        error = f"{type(e).__name__}: {e}"
        print(f"\n[FAIL] {error}")
        print("\nIf this is an auth error, re-run: python scripts/gmail_auth.py")
        log_target = write_log({"success": False, "error": error})
        if log_target:
            print(f"Logged to: {log_target}")
        return 1

    print(f"\n[OK] Gmail API reachable")
    print(f"  Account:        {detail['address']}")
    print(f"  Messages total: {detail['messages_total']}")
    print(f"  Token expiry:   {detail['token_expiry']}")

    log_target = write_log({"success": True, **detail})
    if log_target:
        print(f"\nLogged to: {log_target}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
