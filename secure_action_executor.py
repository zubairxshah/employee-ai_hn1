"""
Secure Action Executor
Implements sandboxing, dry-run mode, and audit logging for all actions
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from security_config import get_security_config


class SecureActionExecutor:
    """Secure executor for all external actions"""
    
    def __init__(self):
        self.security_config = get_security_config()
        self.logger = logging.getLogger('SecureActionExecutor')
        
    def send_email(self, to: str, subject: str, body: str, 
                   amount: float = 0, is_bulk: bool = False) -> Dict[str, Any]:
        """Securely send an email with audit logging"""
        action_type = "email_send"
        parameters = {
            "to": to,
            "subject": subject,
            "body_length": len(body)
        }
        
        # Check if action needs approval
        needs_approval = (
            self.security_config.is_approved_action(action_type, amount, to) == False or
            is_bulk
        )
        
        if needs_approval:
            approval_status = "pending"
            result = "held_for_approval"
        else:
            approval_status = "auto_approved"
            result = "executed"
        
        # Check rate limits
        if not self.security_config.check_rate_limit(action_type):
            result = "rate_limited"
            approval_status = "denied"
        
        # Execute or simulate execution based on mode
        if self.security_config.dry_run:
            self.logger.info(f'[DRY RUN] Would send email to {to}')
            if result == "executed":
                result = "dry_run_executed"
        else:
            if result == "executed":
                # In a real implementation, this would actually send the email
                self.logger.info(f'Sent email to {to}')
        
        # Log the action
        self.security_config.log_action(
            action_type=action_type,
            actor="claude_code",
            target=to,
            parameters=parameters,
            approval_status=approval_status,
            result=result
        )
        
        return {
            "success": result in ["executed", "dry_run_executed"],
            "status": result,
            "approval_status": approval_status
        }
    
    def make_payment(self, recipient: str, amount: float, description: str) -> Dict[str, Any]:
        """Securely make a payment with audit logging"""
        action_type = "payment"
        parameters = {
            "recipient": recipient,
            "amount": amount,
            "description": description
        }
        
        # Check if action needs approval
        needs_approval = (
            self.security_config.is_approved_action(action_type, amount, recipient) == False or
            amount > 100  # Additional check for payments over $100
        )
        
        if needs_approval:
            approval_status = "pending"
            result = "held_for_approval"
        else:
            approval_status = "auto_approved"
            result = "executed"
        
        # Check rate limits
        if not self.security_config.check_rate_limit(action_type):
            result = "rate_limited"
            approval_status = "denied"
        
        # Execute or simulate execution based on mode
        if self.security_config.dry_run:
            self.logger.info(f'[DRY RUN] Would make payment of ${amount} to {recipient}')
            if result == "executed":
                result = "dry_run_executed"
        else:
            if result == "executed":
                # In a real implementation, this would actually make the payment
                self.logger.info(f'Made payment of ${amount} to {recipient}')
        
        # Log the action
        self.security_config.log_action(
            action_type=action_type,
            actor="claude_code",
            target=recipient,
            parameters=parameters,
            approval_status=approval_status,
            result=result,
            approved_by="system" if approval_status == "auto_approved" else "pending"
        )
        
        return {
            "success": result in ["executed", "dry_run_executed"],
            "status": result,
            "approval_status": approval_status
        }
    
    def post_social_media(self, platform: str, content: str, is_reply: bool = False) -> Dict[str, Any]:
        """Securely post to social media with audit logging"""
        action_type = f"{platform}_post"
        parameters = {
            "platform": platform,
            "content_length": len(content),
            "is_reply": is_reply
        }
        
        # Check if action needs approval
        needs_approval = (
            is_reply or  # Replies always require approval
            self.security_config.is_approved_action(action_type, 0, "reply" if is_reply else "post")
        )
        
        if needs_approval:
            approval_status = "pending"
            result = "held_for_approval"
        else:
            approval_status = "auto_approved"
            result = "executed"
        
        # Execute or simulate execution based on mode
        if self.security_config.dry_run:
            self.logger.info(f'[DRY RUN] Would post to {platform}')
            if result == "executed":
                result = "dry_run_executed"
        else:
            if result == "executed":
                # In a real implementation, this would actually post
                self.logger.info(f'Posted to {platform}')
        
        # Log the action
        self.security_config.log_action(
            action_type=action_type,
            actor="claude_code",
            target=platform,
            parameters=parameters,
            approval_status=approval_status,
            result=result
        )
        
        return {
            "success": result in ["executed", "dry_run_executed"],
            "status": result,
            "approval_status": approval_status
        }
    
    def file_operation(self, operation: str, file_path: str, destination: str = None) -> Dict[str, Any]:
        """Securely perform file operations with audit logging"""
        action_type = f"file_{operation}"
        parameters = {
            "operation": operation,
            "file_path": file_path,
            "destination": destination
        }
        
        # Check if operation is outside vault (requires approval)
        vault_path = str(self.security_config.vault_path)
        needs_approval = False
        
        if operation == "move" and destination and not destination.startswith(vault_path):
            needs_approval = True
            parameters["outside_vault"] = True
        
        if operation == "delete":
            needs_approval = True  # All deletes require approval
        
        if needs_approval:
            approval_status = "pending"
            result = "held_for_approval"
        else:
            approval_status = "auto_approved"
            result = "executed"
        
        # Execute or simulate execution based on mode
        if self.security_config.dry_run:
            self.logger.info(f'[DRY RUN] Would perform {operation} on {file_path}')
            if result == "executed":
                result = "dry_run_executed"
        else:
            if result == "executed":
                # In a real implementation, this would actually perform the file operation
                self.logger.info(f'Performed {operation} on {file_path}')
        
        # Log the action
        self.security_config.log_action(
            action_type=action_type,
            actor="claude_code",
            target=file_path,
            parameters=parameters,
            approval_status=approval_status,
            result=result
        )
        
        return {
            "success": result in ["executed", "dry_run_executed"],
            "status": result,
            "approval_status": approval_status
        }


# Global secure action executor instance
secure_executor = SecureActionExecutor()


def get_secure_executor() -> SecureActionExecutor:
    """Get the global secure action executor instance"""
    return secure_executor