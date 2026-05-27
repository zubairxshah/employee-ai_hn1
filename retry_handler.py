"""
Retry Handler for AI Personal Employee
Implements exponential backoff retry logic for transient errors
"""

import time
import logging
from functools import wraps
from enum import Enum
from typing import Type, Tuple, Callable, Any


class ErrorCategory(Enum):
    TRANSIENT = "transient"
    AUTHENTICATION = "authentication"
    LOGIC = "logic"
    DATA = "data"
    SYSTEM = "system"


class TransientError(Exception):
    """Exception for transient errors that can be retried"""
    pass


class AuthenticationError(Exception):
    """Exception for authentication errors"""
    pass


class LogicError(Exception):
    """Exception for logic errors that require human review"""
    pass


class DataError(Exception):
    """Exception for data errors"""
    pass


class SystemError(Exception):
    """Exception for system errors"""
    pass


def with_retry(max_attempts: int = 3, base_delay: float = 1, max_delay: float = 60, 
               retry_exceptions: Tuple[Type[Exception], ...] = (TransientError,)):
    """
    Decorator to add retry logic with exponential backoff to functions
    
    Args:
        max_attempts: Maximum number of attempts
        base_delay: Initial delay between retries (seconds)
        max_delay: Maximum delay between retries (seconds)
        retry_exceptions: Tuple of exception types to retry
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except retry_exceptions as e:
                    last_exception = e
                    if attempt == max_attempts - 1:
                        # Final attempt failed, raise the exception
                        raise
                    
                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    
                    logging.warning(f'Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {str(e)}. '
                                  f'Retrying in {delay}s...')
                    time.sleep(delay)
                except Exception as e:
                    # If it's not a retryable exception, don't retry
                    raise
            
            # This shouldn't be reached, but just in case
            if last_exception:
                raise last_exception
        
        return wrapper
    return decorator


def categorize_error(exception: Exception) -> ErrorCategory:
    """
    Categorize an error based on its type
    
    Args:
        exception: The exception to categorize
        
    Returns:
        ErrorCategory: The category of the error
    """
    if isinstance(exception, TransientError):
        return ErrorCategory.TRANSIENT
    elif isinstance(exception, AuthenticationError):
        return ErrorCategory.AUTHENTICATION
    elif isinstance(exception, LogicError):
        return ErrorCategory.LOGIC
    elif isinstance(exception, DataError):
        return ErrorCategory.DATA
    elif isinstance(exception, SystemError):
        return ErrorCategory.SYSTEM
    else:
        # Default to transient for unknown errors
        return ErrorCategory.TRANSIENT


def handle_error(error: Exception, context: str = "") -> bool:
    """
    Handle an error based on its category
    
    Args:
        error: The error to handle
        context: Context information about where the error occurred
        
    Returns:
        bool: True if the error was handled and system can continue, False otherwise
    """
    error_category = categorize_error(error)
    logging.error(f"Error in {context}: {error_category.value} - {str(error)}")
    
    if error_category == ErrorCategory.TRANSIENT:
        # Transient errors are handled by retry logic
        logging.info(f"Transient error in {context}, will be handled by retry mechanism")
        return True
    elif error_category == ErrorCategory.AUTHENTICATION:
        # Authentication errors require human intervention
        logging.critical(f"Authentication error in {context}, pausing operations and alerting human")
        # In a real implementation, this would trigger an alert to the human operator
        return False
    elif error_category == ErrorCategory.LOGIC:
        # Logic errors require human review
        logging.warning(f"Logic error in {context}, queuing for human review")
        # In a real implementation, this would add the item to a human review queue
        return True
    elif error_category == ErrorCategory.DATA:
        # Data errors should quarantine the problematic data
        logging.error(f"Data error in {context}, quarantining and alerting")
        # In a real implementation, this would quarantine the data and alert
        return True
    elif error_category == ErrorCategory.SYSTEM:
        # System errors may require system restart
        logging.critical(f"System error in {context}, may require restart")
        return False
    
    return True


# Example usage functions
@with_retry(max_attempts=3, base_delay=1, max_delay=10)
def example_transient_operation():
    """Example operation that might have transient failures"""
    import random
    if random.random() < 0.7:  # 70% chance of failure
        raise TransientError("Network timeout occurred")
    return "Success!"


def example_error_handling():
    """Example of error handling in action"""
    try:
        result = example_transient_operation()
        print(f"Operation succeeded: {result}")
    except Exception as e:
        handled = handle_error(e, "example_operation")
        if not handled:
            print("Error could not be handled, system may need intervention")
        else:
            print("Error handled, system continuing")


if __name__ == "__main__":
    # Test the retry mechanism
    print("Testing retry mechanism...")
    example_error_handling()