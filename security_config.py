"""
Security Configuration for AI Personal Employee
Implements credential management, sandboxing, and permission boundaries
"""

import os
from pathlib import Path
import logging
from datetime import datetime
import json
from typing import Dict, Any, Optional


class SecurityConfig:
    """Security configuration and utilities"""

    # Credentials that must NEVER be loaded on the cloud agent
    SENSITIVE_CREDENTIALS = {
        'GMAIL_APP_PASSWORD',
        'WHATSAPP_NOTIFICATION_PHONE',
        'WHATSAPP_SESSION_PATH',
        'BANK_API_TOKEN',
    }

    def __init__(self):
        self.dev_mode = os.getenv('DEV_MODE', 'true').lower() == 'true'
        self.dry_run = os.getenv('DRY_RUN', 'true').lower() == 'true'
        self.vault_path = Path(os.getenv('VAULT_PATH', r'D:\prompteng\AI_Employee_Vault'))
        self.logs_dir = self.vault_path / "Logs"

        # Ensure logs directory exists
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # Permission boundaries
        self.permission_boundaries = {
            'email': {
                'auto_approve_threshold': 50,  # dollars
                'always_require_approval': ['new_contacts', 'bulk_sends']
            },
            'payments': {
                'auto_approve_threshold': 100,  # dollars
                'always_require_approval': ['new_payees', 'large_payments']
            },
            'social_media': {
                'auto_approve_threshold': None,
                'always_require_approval': ['replies', 'dms']
            },
            'file_operations': {
                'auto_approve_threshold': None,
                'always_require_approval': ['delete', 'move_outside_vault']
            }
        }
        
        # Rate limiting
        self.rate_limits = {
            'emails_per_hour': int(os.getenv('MAX_EMAILS_PER_HOUR', '10')),
            'payments_per_hour': int(os.getenv('MAX_PAYMENTS_PER_HOUR', '3'))
        }
        
        # Initialize logger
        self.logger = self._setup_logger()
    
    def _setup_logger(self):
        """Set up the security logger"""
        logger = logging.getLogger('AI_Employee_Security')
        logger.setLevel(logging.INFO)
        
        # Create file handler for security logs
        log_file = self.logs_dir / f"{datetime.now().strftime('%Y-%m-%d')}_security.log"
        handler = logging.FileHandler(log_file)
        handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        
        logger.addHandler(handler)
        return logger
    
    def get_credential(self, credential_name: str) -> Optional[str]:
        """Securely retrieve a credential from environment variables"""
        return os.getenv(credential_name.upper())
    
    def is_approved_action(self, action_type: str, amount: float = 0, target: str = "") -> bool:
        """Check if an action can be auto-approved based on permission boundaries"""
        if action_type in self.permission_boundaries:
            boundary = self.permission_boundaries[action_type]
            threshold = boundary.get('auto_approve_threshold')
            
            # If there's a threshold, check if amount is below it
            if threshold is not None and amount <= threshold:
                return True
            
            # Check if action always requires approval
            always_approve_list = boundary.get('always_require_approval', [])
            if target in always_approve_list:
                return False
        
        # Default to requiring approval for safety
        return False
    
    def check_rate_limit(self, action_type: str) -> bool:
        """Check if an action is within rate limits"""
        if action_type in self.rate_limits:
            # In a real implementation, we would track actual usage
            # For now, we'll just return True
            return True
        return True
    
    def log_action(self, action_type: str, actor: str, target: str, 
                   parameters: Dict[str, Any], approval_status: str, 
                   result: str, approved_by: str = "system"):
        """Log an action for audit purposes"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action_type": action_type,
            "actor": actor,
            "target": target,
            "parameters": parameters,
            "approval_status": approval_status,
            "approved_by": approved_by,
            "result": result
        }
        
        # Write to daily log file
        log_file = self.logs_dir / f"{datetime.now().strftime('%Y-%m-%d')}.json"
        
        # Read existing logs if file exists
        existing_logs = []
        if log_file.exists():
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if content.strip():
                        existing_logs = json.loads(content)
                    else:
                        existing_logs = []
            except (json.JSONDecodeError, FileNotFoundError):
                existing_logs = []
        
        # Append new log entry
        existing_logs.append(log_entry)
        
        # Write back to file
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(existing_logs, f, indent=2)
        
        # Also log to security log
        self.logger.info(f"Action logged: {action_type} by {actor} on {target}, "
                         f"status: {approval_status}, result: {result}")
    
    def sanitize_input(self, input_text: str) -> str:
        """Sanitize input to prevent injection attacks"""
        # Remove potentially dangerous characters/sequences
        sanitized = input_text.replace('\0', '')  # Null bytes
        sanitized = sanitized.replace('..', '')   # Directory traversal
        # Add more sanitization as needed
        return sanitized

    def validate_cloud_safety(self) -> bool:
        """
        Validate that no sensitive credentials are loaded when running as cloud agent.
        Returns True if safe, False if a sensitive credential was found.
        """
        from agent_config import is_cloud
        if not is_cloud():
            return True

        violations = []
        for cred_name in self.SENSITIVE_CREDENTIALS:
            value = os.getenv(cred_name)
            if value and value.strip():
                violations.append(cred_name)

        if violations:
            self.logger.critical(
                f"CLOUD SAFETY VIOLATION: Sensitive credentials found in environment: "
                f"{', '.join(violations)}. Cloud agent must NOT have access to these."
            )
            return False

        self.logger.info("Cloud safety validation passed")
        return True


# Global security configuration instance
security_config = SecurityConfig()


def get_security_config() -> SecurityConfig:
    """Get the global security configuration instance"""
    return security_config