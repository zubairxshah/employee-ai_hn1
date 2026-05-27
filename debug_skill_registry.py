"""
Debug Skill Registry
"""

import sys
sys.path.insert(0, 'D:\\prompteng\\employee')

# Import skills to trigger registration
from skills.action import OdooMCPActionSkill

from skills.registry import get_registry

registry = get_registry()

# Discover skills from the action module
from pathlib import Path
skills_dir = Path('D:\\prompteng\\employee\\skills')
count = registry.discover_skills(skills_dir / 'action', 'skills.action')
print(f"Discovered {count} skills from action module")

print("\nAll registered skills:")
for skill_name in registry.list_skills():
    print(f"  - {skill_name}")

# Try to get the Odoo skill
print("\nTrying to get odoo_mcp_action skill...")
skill = registry.get('odoo_mcp_action')
if skill:
    print(f"[PASS] Skill found: {skill.name}")
    print(f"  Description: {skill.get_capability_description()}")
else:
    print("[FAIL] Skill not found")
    
# Also try with get_skill
from skills.registry import get_skill
skill = get_skill('odoo_mcp_action')
if skill:
    print(f"[PASS] get_skill found: {skill.name}")
else:
    print("[FAIL] get_skill did not find the skill")
