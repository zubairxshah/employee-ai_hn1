"""
Platinum Tier Demo Script
Interactive demo: simulates cloud + local agents using the same vault.

Usage:
    python run_demo.py

This runs in a single process, simulating both agents by switching AGENT_ROLE.
For real two-terminal testing:
    Terminal 1: set AGENT_ROLE=cloud && python cloud_orchestrator.py
    Terminal 2: set AGENT_ROLE=local && python local_orchestrator.py
"""

import os
import sys
import time
import importlib
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

VAULT_PATH = os.getenv("VAULT_PATH", r"D:\prompteng\AI_Employee_Vault")


def banner(text):
    print(f"\n{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}\n")


def step(num, text):
    print(f"\n--- Step {num}: {text} ---")


def switch_role(role):
    """Switch agent role by reloading agent_config."""
    os.environ['AGENT_ROLE'] = role
    os.environ['AGENT_ID'] = f'{role}-demo-{os.getpid()}'
    import agent_config
    importlib.reload(agent_config)
    print(f"  [Role switched to: {role.upper()}]")


def main():
    banner("Platinum Tier Demo")
    print(f"Vault: {VAULT_PATH}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # ==================== SETUP ====================
    step(0, "Setup - Create demo task in Needs_Action/email/")

    task_dir = Path(VAULT_PATH) / "Needs_Action" / "email"
    task_dir.mkdir(parents=True, exist_ok=True)

    task_file = task_dir / "DEMO_email_task.md"
    task_file.write_text("""---
to: demo-client@example.com
subject: Monthly Report - March 2026
type: email
---

## Email Task

Dear Client,

Please find attached the monthly report for March 2026.
Revenue is up 15% compared to last month.

Best regards,
AI Employee
""", encoding="utf-8")
    print(f"  Created: {task_file}")

    # ==================== CLOUD AGENT ====================
    step(1, "Cloud Agent - Claim task from Needs_Action/email/")
    switch_role("cloud")

    from claim_manager import ClaimManager
    from dashboard_manager import DashboardManager

    cloud_claim = ClaimManager()
    cloud_dashboard = DashboardManager()

    available = cloud_claim.list_available(domain="email")
    print(f"  Available tasks: {len(available)}")

    if not available:
        print("  ERROR: No tasks found!")
        return

    claimed = cloud_claim.claim(available[0])
    if claimed:
        print(f"  Claimed: {claimed.name}")
    else:
        print("  ERROR: Failed to claim task!")
        return

    # ==================== CLOUD CREATES DRAFT ====================
    step(2, "Cloud Agent - Create email draft in Pending_Approval/")

    content = claimed.read_text(encoding="utf-8")
    draft_dir = Path(VAULT_PATH) / "Pending_Approval" / "email"
    draft_dir.mkdir(parents=True, exist_ok=True)

    draft_file = draft_dir / f"EMAIL_DRAFT_demo_{datetime.now().strftime('%H%M%S')}.md"
    draft_file.write_text(f"""---
type: send_email
action: send_email
to: demo-client@example.com
subject: Monthly Report - March 2026
created_by: cloud-demo
created_at: {datetime.now().isoformat()}
status: pending_approval
---

## Email Draft

**To:** demo-client@example.com
**Subject:** Monthly Report - March 2026

### Body
Dear Client,

Please find attached the monthly report for March 2026.
Revenue is up 15% compared to last month.

Best regards,
AI Employee

---
*Draft created by Cloud Agent. Approve to send.*
""", encoding="utf-8")
    print(f"  Draft created: {draft_file.name}")

    # Move claimed task to Done
    cloud_claim.release_done(claimed, domain="email")
    print(f"  Original task moved to Done/")

    # Write dashboard update
    cloud_dashboard.write_update("email_draft", {
        "summary": f"Email draft created: {draft_file.name}",
        "to": "demo-client@example.com",
    })
    print(f"  Dashboard update written")

    # Write signal
    cloud_dashboard.write_signal("new_draft_ready", {
        "domain": "email",
        "filename": draft_file.name,
    })
    print(f"  Signal written for Local agent")

    # ==================== SIMULATE APPROVAL ====================
    step(3, "Human Approval - Move draft to Approved/ (simulated)")

    approved_dir = Path(VAULT_PATH) / "Approved" / "email"
    approved_dir.mkdir(parents=True, exist_ok=True)
    approved_path = approved_dir / draft_file.name

    os.rename(str(draft_file), str(approved_path))
    print(f"  Moved to Approved: {approved_path.name}")
    print(f"  (In production, this happens via Obsidian vault)")

    # ==================== LOCAL AGENT ====================
    step(4, "Local Agent - Process approved email")
    switch_role("local")

    import agent_config
    print(f"  can_execute_action('send_email'): {agent_config.can_execute_action('send_email')}")

    # Merge dashboard updates
    importlib.reload(sys.modules.get('dashboard_manager', importlib.import_module('dashboard_manager')))
    from dashboard_manager import DashboardManager
    local_dashboard = DashboardManager()
    merged = local_dashboard.merge_updates_into_dashboard()
    print(f"  Merged {merged} update(s) into Dashboard.md")

    # Read signals
    signals = local_dashboard.read_signals()
    for sig in signals:
        print(f"  Signal received: {sig.get('signal')} - {sig.get('data', {}).get('filename', '')}")

    # Execute the approved email (simulated - just move to Done)
    step(5, "Local Agent - Execute approved action (simulated send)")

    done_dir = Path(VAULT_PATH) / "Done" / "email"
    done_dir.mkdir(parents=True, exist_ok=True)
    done_path = done_dir / approved_path.name

    # In production, Local would call email MCP here
    print(f"  [DRY RUN] Would send email to demo-client@example.com")
    print(f"  [DRY RUN] Subject: Monthly Report - March 2026")

    os.rename(str(approved_path), str(done_path))
    print(f"  Moved to Done: {done_path.name}")

    # ==================== VERIFICATION ====================
    step(6, "Verification")

    checks = [
        ("Task removed from Needs_Action", not (task_dir / "DEMO_email_task.md").exists()),
        ("Draft not in Pending_Approval", not draft_file.exists()),
        ("Draft not in Approved", not approved_path.exists()),
        ("Draft in Done", done_path.exists()),
        ("Dashboard.md exists", (Path(VAULT_PATH) / "Dashboard.md").exists()),
    ]

    all_pass = True
    for label, result in checks:
        status = "PASS" if result else "FAIL"
        print(f"  [{status}] {label}")
        if not result:
            all_pass = False

    banner(f"Demo {'PASSED' if all_pass else 'FAILED'}")

    if all_pass:
        print("The Platinum tier flow works correctly:")
        print("  1. Cloud agent claimed email task from Needs_Action/")
        print("  2. Cloud created draft in Pending_Approval/email/")
        print("  3. Human approved (moved to Approved/)")
        print("  4. Local agent executed approved action")
        print("  5. File moved to Done/")
        print("  6. Dashboard updated, signals consumed")
        print()
        print("For real two-terminal testing:")
        print("  Terminal 1: set AGENT_ROLE=cloud && python cloud_orchestrator.py")
        print("  Terminal 2: set AGENT_ROLE=local && python local_orchestrator.py")

    # Cleanup demo files
    try:
        done_path.unlink(missing_ok=True)
    except:
        pass


if __name__ == "__main__":
    main()
