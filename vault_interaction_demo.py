# Vault Interaction Script
# This script demonstrates how Claude/Qwen would interact with the Obsidian vault

import os
import json
import time
from datetime import datetime

# Configuration
VAULT_PATH = r"D:\prompteng\AI_Employee_Vault"
DASHBOARD_FILE = os.path.join(VAULT_PATH, "Dashboard.md")
COMPANY_HANDBOOK_FILE = os.path.join(VAULT_PATH, "Company_Handbook.md")

def read_dashboard():
    """Read the current state of the dashboard"""
    try:
        with open(DASHBOARD_FILE, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"Dashboard file not found at {DASHBOARD_FILE}")
        return None

def update_dashboard(section, content):
    """Update a specific section of the dashboard"""
    try:
        with open(DASHBOARD_FILE, 'r', encoding='utf-8') as f:
            dashboard_content = f.read()
        
        # Find and replace the section
        start_marker = f"## {section}"
        end_marker = "\n## "  # Next section
        
        start_idx = dashboard_content.find(start_marker)
        if start_idx == -1:
            print(f"Section '{section}' not found in dashboard")
            return False
            
        # Find the end of the section
        end_idx = dashboard_content.find(end_marker, start_idx + len(start_marker))
        if end_idx == -1:
            end_idx = len(dashboard_content)  # Last section
        
        # Extract the section to update
        section_content = dashboard_content[start_idx:end_idx]
        
        # Update the content (this is simplified - in practice, you'd parse more carefully)
        updated_section = f"## {section}\n{content}\n\n"
        
        # Replace the old section with the new one
        new_dashboard = dashboard_content[:start_idx] + updated_section
        if end_idx < len(dashboard_content):
            new_dashboard += dashboard_content[end_idx:]
        
        # Write back to file
        with open(DASHBOARD_FILE, 'w', encoding='utf-8') as f:
            f.write(new_dashboard)
        
        print(f"Updated section '{section}' in dashboard")
        return True
    except Exception as e:
        print(f"Error updating dashboard: {str(e)}")
        return False

def read_company_handbook():
    """Read the company handbook for rules of engagement"""
    try:
        with open(COMPANY_HANDBOOK_FILE, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"Company handbook not found at {COMPANY_HANDBOOK_FILE}")
        return None

def process_task(task_description):
    """Process a task according to company handbook rules"""
    handbook = read_company_handbook()
    if not handbook:
        print("Could not read company handbook")
        return False
    
    # This is where Claude/Qwen would apply reasoning based on the handbook
    # For demonstration, we'll just log the task
    print(f"Processing task: {task_description}")
    
    # Example: Check if task involves financial transaction over $500
    if "$" in task_description:
        # Extract amount (simplified)
        import re
        amounts = re.findall(r'\$(\d+)', task_description)
        for amount_str in amounts:
            amount = int(amount_str)
            if amount > 500:
                print(f"FLAGGED: Financial transaction over $500 detected (${amount}). Requires human approval.")
                # In real implementation, this would create a pending approval item
                return "requires_approval"
    
    # Update dashboard with task status
    update_dashboard("Status Overview", f"- **Last Check:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n- **Active Watchers:** File system, Gmail\n- **Pending Actions:** 0\n- **Completed Today:** 1")
    
    print(f"Task completed: {task_description}")
    return "completed"

def main():
    """Main function demonstrating vault interaction"""
    print("AI Employee Vault Interaction Demo")
    print("=" * 40)
    
    # Read current dashboard
    dashboard = read_dashboard()
    if dashboard:
        print("Current dashboard loaded")
    
    # Example task processing
    example_tasks = [
        "Send follow-up email to client about project quote of $300",
        "Process payment for supplier invoice of $750",
        "Schedule meeting with marketing team"
    ]
    
    for task in example_tasks:
        result = process_task(task)
        print(f"Task result: {result}\n")
        time.sleep(1)  # Simulate processing time

if __name__ == "__main__":
    main()