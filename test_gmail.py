"""Test Gmail Watcher Skill"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from pathlib import Path

# Import skill modules explicitly
print("Step 1: Importing GmailWatcherSkill...")
from skills.perception import GmailWatcherSkill
print(f"GmailWatcherSkill: {GmailWatcherSkill}")

# Import registry
print("\nStep 2: Loading registry...")
from skills.registry import get_registry

config_dir = str(Path(__file__).parent / 'skills' / 'config')
print(f"Config directory: {config_dir}")

registry = get_registry(config_dir)
print(f"Registry loaded: {registry}")

# List skills
print("\nStep 3: Listing registered skills...")
skills = registry.list_skills()
print(f"Registered skills ({len(skills)}): {skills}")

# Get Gmail watcher
print("\nStep 4: Getting gmail_watcher skill...")
gmail_skill = registry.get('gmail_watcher')
print(f"Gmail skill: {gmail_skill}")

if gmail_skill:
    # Test without scanning
    print("\nStep 5: Testing skill (no scan)...")
    result = gmail_skill.run(
        {'vault_path': r'D:\prompteng\AI_Employee_Vault'},
        {'vault_path': r'D:\prompteng\AI_Employee_Vault', 'scan': False}
    )
    print(f"Result: {result}")
    
    # Check credentials
    print("\nStep 6: Checking credentials...")
    creds = gmail_skill._get_credentials()
    print(f"Credentials: {creds}")
    
    if creds:
        print("\nStep 7: Testing email fetch (scan=True)...")
        result = gmail_skill.run(
            {'vault_path': r'D:\prompteng\AI_Employee_Vault'},
            {'vault_path': r'D:\prompteng\AI_Employee_Vault', 'scan': True}
        )
        print(f"Scan result: {result}")
else:
    print("Gmail skill not found in registry!")
