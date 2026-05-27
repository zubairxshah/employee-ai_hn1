# Action Skills
# Skills for performing external actions via MCP servers

from .filesystem_mcp_action import FilesystemMCPActionSkill
from .approval_mcp_action import ApprovalMCPActionSkill
from .email_mcp_action import EmailMCPActionSkill
from .odoo_mcp_action import OdooMCPActionSkill
from .facebook_mcp_action import FacebookMCPActionSkill
from .twitter_mcp_action import TwitterMCPActionSkill

__all__ = [
    'FilesystemMCPActionSkill',
    'ApprovalMCPActionSkill',
    'EmailMCPActionSkill',
    'OdooMCPActionSkill',
    'FacebookMCPActionSkill',
    'TwitterMCPActionSkill',
]
