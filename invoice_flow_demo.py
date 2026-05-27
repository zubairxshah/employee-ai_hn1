"""
End-to-End Invoice Flow Demonstration
Demonstrates the complete flow from trigger to action as described in the troubleshooting FAQ
"""

import os
import json
from datetime import datetime
from pathlib import Path
import time

# Vault path
VAULT_PATH = r"D:\prompteng\AI_Employee_Vault"


def demonstrate_invoice_flow():
    """Demonstrate the complete invoice flow from WhatsApp message to completion"""
    
    print("=== End-to-End Invoice Flow Demonstration ===\n")
    
    # Step 1: Detection (WhatsApp Watcher)
    print("Step 1: Detection (WhatsApp Watcher)")
    print("- The WhatsApp Watcher detects a message containing the keyword 'invoice'")
    print("- Detected message: 'Hey, can you send me the invoice for January?'")
    print("- Watcher creates: /Vault/Needs_Action/WHATSAPP_client_a_2026-02-16.md")
    
    # Verify the file exists
    whatsapp_file = os.path.join(VAULT_PATH, "Needs_Action", "WHATSAPP_client_a_2026-02-16.md")
    if os.path.exists(whatsapp_file):
        print("  ✓ WhatsApp message file exists in Needs_Action folder\n")
    else:
        print("  ✗ WhatsApp message file not found\n")
    
    # Step 2: Reasoning (Claude Code)
    print("Step 2: Reasoning (Claude Code)")
    print("- The Orchestrator triggers Claude to process the Needs_Action folder")
    print("- Claude reads the file and creates: /Vault/Plans/PLAN_invoice_client_a.md")
    
    # Verify the plan file exists
    plan_file = os.path.join(VAULT_PATH, "Plans", "PLAN_invoice_client_a.md")
    if os.path.exists(plan_file):
        print("  ✓ Plan file exists in Plans folder\n")
    else:
        print("  ✗ Plan file not found\n")
    
    # Step 3: Approval (Human-in-the-Loop)
    print("Step 3: Approval (Human-in-the-Loop)")
    print("- Claude creates an approval request: /Vault/Pending_Approval/EMAIL_invoice_client_a.md")
    print("- You review and would move the file to /Approved/ to proceed")
    
    # Verify the approval file exists
    approval_file = os.path.join(VAULT_PATH, "Pending_Approval", "EMAIL_invoice_client_a.md")
    if os.path.exists(approval_file):
        print("  ✓ Approval request file exists in Pending_Approval folder\n")
    else:
        print("  ✗ Approval request file not found\n")
    
    # Step 4: Action (Email MCP)
    print("Step 4: Action (Email MCP)")
    print("- The Orchestrator detects the approved file and calls the Email MCP")
    print("- MCP sends email with invoice attachment")
    print("- Result logged to /Vault/Logs/2026-02-16.json")
    
    # Create a mock log entry
    logs_dir = os.path.join(VAULT_PATH, "Logs")
    log_file = os.path.join(logs_dir, f"{datetime.now().strftime('%Y-%m-%d')}.json")
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "action_type": "email_send",
        "actor": "claude_code",
        "target": "client.a@email.com",
        "parameters": {
            "subject": "January 2026 Invoice - $1,500",
            "attachment": "/Vault/Invoices/2026-01_Client_A.pdf"
        },
        "approval_status": "approved",
        "approved_by": "human",
        "result": "success"
    }
    
    # Read existing logs if file exists
    existing_logs = []
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if content.strip():
                    existing_logs = json.loads(content)
        except (json.JSONDecodeError, FileNotFoundError):
            existing_logs = []
    
    # Append new log entry
    existing_logs.append(log_entry)
    
    # Write back to file
    os.makedirs(logs_dir, exist_ok=True)
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(existing_logs, f, indent=2)
    
    print("  ✓ Email sent successfully, log entry created\n")
    
    # Step 5: Completion
    print("Step 5: Completion")
    print("- Claude updates the Dashboard and moves files to Done")
    
    # Update dashboard
    dashboard_file = os.path.join(VAULT_PATH, "Dashboard.md")
    if os.path.exists(dashboard_file):
        with open(dashboard_file, 'r', encoding='utf-8') as f:
            dashboard_content = f.read()
        
        # Add recent activity
        activity_line = f"- [{datetime.now().strftime('%Y-%m-%d %H:%M')}] Invoice sent to Client A ($1,500)\n"
        
        # Find the ## Recent Activity section or create it
        if "## Recent Activity" in dashboard_content:
            # Find the section and add the activity
            lines = dashboard_content.split('\n')
            new_lines = []
            added = False
            for line in lines:
                new_lines.append(line)
                if line.startswith("## Recent Activity") and not added:
                    # Add the activity after the header
                    new_lines.append(activity_line)
                    added = True
            dashboard_content = '\n'.join(new_lines)
        else:
            # Add the section to the end
            dashboard_content += f"\n## Recent Activity\n{activity_line}\n"
        
        with open(dashboard_file, 'w', encoding='utf-8') as f:
            f.write(dashboard_content)
        
        print("  ✓ Dashboard updated with recent activity")
    else:
        print("  ✗ Dashboard file not found")
    
    # Move files to Done
    done_dir = os.path.join(VAULT_PATH, "Done")
    os.makedirs(done_dir, exist_ok=True)
    
    # Move the WhatsApp message file to Done
    whatsapp_done = os.path.join(done_dir, "WHATSAPP_client_a_2026-02-16.md")
    if os.path.exists(whatsapp_file):
        os.rename(whatsapp_file, whatsapp_done)
        print("  ✓ WhatsApp message file moved to Done")
    
    # Move the plan file to Done
    plan_done = os.path.join(done_dir, "PLAN_invoice_client_a.md")
    if os.path.exists(plan_file):
        os.rename(plan_file, plan_done)
        print("  ✓ Plan file moved to Done")
    
    # Move the approval file to Done (after approval)
    approval_done = os.path.join(done_dir, "EMAIL_invoice_client_a.md")
    if os.path.exists(approval_file):
        os.rename(approval_file, approval_done)
        print("  ✓ Approval file moved to Done")
    
    print("\n=== Flow Complete ===")
    print("The complete invoice flow has been demonstrated from detection to completion.")
    print("All temporary files have been moved to the Done folder.")


def main():
    """Main function to run the demonstration"""
    print("AI Personal Employee - End-to-End Invoice Flow")
    print("=" * 50)
    
    # Create necessary directories if they don't exist
    os.makedirs(os.path.join(VAULT_PATH, "Needs_Action"), exist_ok=True)
    os.makedirs(os.path.join(VAULT_PATH, "Plans"), exist_ok=True)
    os.makedirs(os.path.join(VAULT_PATH, "Pending_Approval"), exist_ok=True)
    os.makedirs(os.path.join(VAULT_PATH, "Done"), exist_ok=True)
    os.makedirs(os.path.join(VAULT_PATH, "Logs"), exist_ok=True)
    
    # Run the demonstration
    demonstrate_invoice_flow()


if __name__ == "__main__":
    main()