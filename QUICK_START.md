# Quick Start Guide

## Setting Up Your AI Personal Employee

### Prerequisites
- Python 3.8+
- uv package manager
- Access to Claude Code API (or Qwen CLI)

### Step 1: Clone/Setup the Repository
```bash
# Navigate to your desired directory
cd D:\prompteng\
```

### Step 2: Install Dependencies
```bash
uv pip install -r requirements.txt
```

### Step 3: Set Up the Obsidian Vault
1. Create the vault directory:
   ```bash
   mkdir D:\prompteng\AI_Employee_Vault
   ```

2. Copy the initial vault files:
   ```bash
   cp Dashboard.md Company_Handbook.md "D:\prompteng\AI_Employee_Vault\"
   ```

3. Create the required subdirectories:
   ```bash
   mkdir "D:\prompteng\AI_Employee_Vault\Inbox"
   mkdir "D:\prompteng\AI_Employee_Vault\Needs_Action"
   mkdir "D:\prompteng\AI_Employee_Vault\Done"
   ```

### Step 4: Configure Claude Integration
1. Update `.claude/config.json` with your Claude API credentials
2. Verify the vault path in `.claude\vault_integration.json` matches your setup

### Step 5: Run the File Watcher
```bash
python watchers/file_watcher.py
```

### Step 6: Test Vault Integration
```bash
python vault_interaction_demo.py
```

## Understanding the Architecture

### The Nerve Center (Obsidian)
- **Dashboard.md**: Real-time summary of bank balance, pending messages, and active business projects
- **Company_Handbook.md**: Contains your "Rules of Engagement"

### The Muscle (Claude Code/Qwen CLI)
- Interacts with the vault through file system operations
- Implements the Ralph Wiggum loop for continuous processing
- Follows rules defined in the Company Handbook

## Next Steps
After completing the initial setup:
1. Implement the Gmail watcher for Bronze Tier
2. Connect Claude directly to the vault for reading/writing
3. Test the complete workflow with sample tasks
4. Progress through the development tiers as outlined in TIER_INFO.md