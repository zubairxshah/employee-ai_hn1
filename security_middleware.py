"""
Security Middleware for AI Personal Employee
Implements security checks for all orchestrator operations
"""

import functools
import os
from pathlib import Path
from typing import Callable, Any
from security_config import get_security_config


def secure_file_access(func: Callable) -> Callable:
    """Decorator to ensure file operations are within vault boundaries"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        security_config = get_security_config()
        vault_path = security_config.vault_path
        
        # Check if any file path arguments are within the vault
        for arg in args:
            if isinstance(arg, (str, Path)):
                abs_path = Path(arg).resolve()
                if not str(abs_path).startswith(str(vault_path.resolve())):
                    security_config.logger.warning(
                        f"Blocked access to path outside vault: {abs_path}"
                    )
                    raise PermissionError(f"Access denied: path outside vault: {arg}")
        
        for key, value in kwargs.items():
            if isinstance(value, (str, Path)):
                abs_path = Path(value).resolve()
                if not str(abs_path).startswith(str(vault_path.resolve())):
                    security_config.logger.warning(
                        f"Blocked access to path outside vault: {abs_path}"
                    )
                    raise PermissionError(f"Access denied: path outside vault: {value}")
        
        return func(*args, **kwargs)
    return wrapper


def audit_log(action_type: str):
    """Decorator to log actions for audit purposes"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            security_config = get_security_config()
            
            # Execute the function and capture result
            try:
                result = func(*args, **kwargs)
                success = True
                error_msg = None
            except Exception as e:
                success = False
                error_msg = str(e)
                result = None
                raise
            finally:
                # Log the action regardless of success/failure
                security_config.log_action(
                    action_type=action_type,
                    actor="orchestrator",
                    target=f"{func.__module__}.{func.__name__}",
                    parameters={
                        "args_count": len(args),
                        "kwargs_keys": list(kwargs.keys()),
                        "success": success,
                        "error": error_msg
                    },
                    approval_status="system",
                    result="success" if success else "failed",
                    approved_by="system"
                )
            
            return result
        return wrapper
    return decorator


def rate_limit_check(action_type: str):
    """Decorator to check rate limits before executing actions"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            security_config = get_security_config()
            
            # Check rate limit
            if not security_config.check_rate_limit(action_type):
                security_config.logger.warning(
                    f"Rate limit exceeded for {action_type}"
                )
                raise RuntimeError(f"Rate limit exceeded for {action_type}")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def dev_mode_check(func: Callable) -> Callable:
    """Decorator to check if operation is allowed in dev mode"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        security_config = get_security_config()
        
        if security_config.dev_mode:
            # In dev mode, we might want to restrict certain operations
            # For now, just log that we're in dev mode
            security_config.logger.info(
                f"Executing {func.__name__} in dev mode"
            )
        
        return func(*args, **kwargs)
    return wrapper


def dry_run_wrapper(func: Callable) -> Callable:
    """Decorator to wrap functions with dry-run capability"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        security_config = get_security_config()
        
        if security_config.dry_run:
            # Log what would have been done in dry run mode
            security_config.logger.info(
                f"[DRY RUN] Would execute {func.__name__} with args={args}, kwargs={kwargs}"
            )
            # Return a mock result instead of executing
            return {"status": "dry_run_executed", "success": True}
        
        return func(*args, **kwargs)
    return wrapper


# Example usage functions
@secure_file_access
@audit_log("file_operation")
@rate_limit_check("file_operations")
@dev_mode_check
def read_file_secure(path: str) -> str:
    """Securely read a file"""
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


@secure_file_access
@audit_log("file_operation")
@rate_limit_check("file_operations")
@dev_mode_check
def write_file_secure(path: str, content: str) -> bool:
    """Securely write to a file"""
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    return True


@audit_log("external_api_call")
@rate_limit_check("api_calls")
@dry_run_wrapper
def call_external_api(url: str, data: dict) -> dict:
    """Example external API call that supports dry-run"""
    # In a real implementation, this would make an actual API call
    import requests
    response = requests.post(url, json=data)
    return response.json()