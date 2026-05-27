"""
Production Utilities for AI Personal Employee
Provides retry logic, structured logging, health checks, and MCP client
"""

import os
import time
import json
import logging
import requests
from pathlib import Path
from functools import wraps
from datetime import datetime
from typing import Optional, Dict, Any, Callable

from retry_handler import with_retry, TransientError


# ==================== STRUCTURED LOGGING ====================

def get_structured_logger(name: str, log_dir: Optional[str] = None) -> logging.Logger:
    """
    Get a JSON-structured logger that writes to Vault/Logs/.

    Args:
        name: Logger name (used as filename prefix)
        log_dir: Override log directory (defaults to Vault/Logs/)

    Returns:
        Configured logger instance
    """
    if log_dir is None:
        vault_path = os.getenv('VAULT_PATH', r'D:\prompteng\AI_Employee_Vault')
        log_dir = os.path.join(vault_path, 'Logs')

    Path(log_dir).mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(f"employee.{name}")

    # Avoid adding duplicate handlers
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # JSON file handler
    log_file = os.path.join(log_dir, f"{name}.log")
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)

    class JsonFormatter(logging.Formatter):
        def format(self, record):
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            }
            if record.exc_info and record.exc_info[0]:
                log_entry["exception"] = self.formatException(record.exc_info)
            if hasattr(record, 'extra_data'):
                log_entry["data"] = record.extra_data
            return json.dumps(log_entry)

    file_handler.setFormatter(JsonFormatter())
    logger.addHandler(file_handler)

    # Console handler (human-readable)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(
        logging.Formatter('[%(asctime)s] %(levelname)s %(name)s: %(message)s',
                          datefmt='%H:%M:%S')
    )
    logger.addHandler(console_handler)

    return logger


# ==================== MCP RETRY DECORATOR ====================

def mcp_retry(max_attempts: int = 3, base_delay: float = 1.0, max_delay: float = 30.0):
    """
    Decorator for MCP HTTP calls with exponential backoff.
    Wraps the existing retry_handler.py logic, tailored for HTTP requests.

    Retries on: ConnectionError, Timeout, 5xx responses
    Does NOT retry on: 4xx client errors (except 429)

    Args:
        max_attempts: Maximum retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay cap in seconds
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(f"employee.mcp_retry")
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    result = func(*args, **kwargs)

                    # If result is a requests.Response, check for retryable status
                    if isinstance(result, requests.Response):
                        if result.status_code == 429 or result.status_code >= 500:
                            if attempt < max_attempts - 1:
                                delay = min(base_delay * (2 ** attempt), max_delay)
                                logger.warning(
                                    f"Retryable HTTP {result.status_code} from {func.__name__}, "
                                    f"attempt {attempt + 1}/{max_attempts}, retrying in {delay}s"
                                )
                                time.sleep(delay)
                                continue
                    return result

                except (requests.ConnectionError, requests.Timeout) as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        logger.warning(
                            f"{type(e).__name__} in {func.__name__}, "
                            f"attempt {attempt + 1}/{max_attempts}, retrying in {delay}s"
                        )
                        time.sleep(delay)
                    else:
                        raise

                except requests.HTTPError as e:
                    # Don't retry client errors (except 429 handled above)
                    if e.response is not None and 400 <= e.response.status_code < 500:
                        raise
                    last_exception = e
                    if attempt < max_attempts - 1:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        logger.warning(
                            f"HTTPError in {func.__name__}, "
                            f"attempt {attempt + 1}/{max_attempts}, retrying in {delay}s"
                        )
                        time.sleep(delay)
                    else:
                        raise

            if last_exception:
                raise last_exception

        return wrapper
    return decorator


# ==================== HEALTH CHECK ====================

def register_health_check(app, name: str):
    """
    Register a /health endpoint on a Flask app.

    Args:
        app: Flask application instance
        name: Service name for the health response
    """
    @app.route('/health', methods=['GET'])
    def health_check():
        return {
            'status': 'healthy',
            'service': name,
            'timestamp': datetime.now().isoformat(),
            'uptime_check': True
        }, 200

    return app


# ==================== MCP CLIENT ====================

class MCPClient:
    """
    HTTP client for calling MCP server endpoints with retry and logging.
    Replaces ad-hoc _call_mcp() methods across action skills.
    """

    def __init__(self, base_url: str, service_name: str = "mcp",
                 timeout: int = 30, max_retries: int = 3):
        """
        Args:
            base_url: MCP server base URL (e.g., http://localhost:8006)
            service_name: Name for logging
            timeout: Request timeout in seconds
            max_retries: Max retry attempts for transient failures
        """
        self.base_url = base_url.rstrip('/')
        self.service_name = service_name
        self.timeout = timeout
        self.max_retries = max_retries
        self.logger = get_structured_logger(f"mcp_client_{service_name}")

    @mcp_retry(max_attempts=3)
    def _request(self, method: str, endpoint: str,
                 data: Optional[Dict] = None,
                 params: Optional[Dict] = None) -> requests.Response:
        """Make an HTTP request with retry logic."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        response = requests.request(
            method=method,
            url=url,
            json=data,
            params=params,
            timeout=self.timeout
        )
        return response

    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """GET request to MCP endpoint."""
        try:
            response = self._request('GET', endpoint, params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            self.logger.error(f"GET {endpoint} failed: {e}")
            return {"success": False, "error": f"MCP request failed: {str(e)}"}

    def post(self, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """POST request to MCP endpoint."""
        try:
            response = self._request('POST', endpoint, data=data)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            self.logger.error(f"POST {endpoint} failed: {e}")
            return {"success": False, "error": f"MCP request failed: {str(e)}"}

    def health(self) -> Dict[str, Any]:
        """Check MCP server health."""
        return self.get('health')


# ==================== HEALTH AGGREGATOR ====================

class HealthAggregator:
    """
    Aggregates health check results from multiple services.
    Used by cloud_health_monitor and watchdog.
    """

    def __init__(self):
        self.results: Dict[str, Dict[str, Any]] = {}
        self.logger = get_structured_logger("health_aggregator")

    def check_service(self, name: str, client: MCPClient) -> Dict[str, Any]:
        """Check a single service and store the result."""
        try:
            health = client.health()
            is_healthy = health.get("status") == "healthy"
            result = {
                "status": "healthy" if is_healthy else "unhealthy",
                "response": health,
                "checked_at": datetime.now().isoformat(),
            }
        except Exception as e:
            result = {
                "status": "unreachable",
                "error": str(e),
                "checked_at": datetime.now().isoformat(),
            }

        self.results[name] = result
        return result

    def get_overall_status(self) -> str:
        """Return 'healthy' if all services healthy, else 'degraded'."""
        if not self.results:
            return "unknown"
        for result in self.results.values():
            if result.get("status") != "healthy":
                return "degraded"
        return "healthy"

    def get_unhealthy_services(self) -> list:
        """Return list of unhealthy service names."""
        return [
            name for name, result in self.results.items()
            if result.get("status") != "healthy"
        ]

    def to_dict(self) -> Dict[str, Any]:
        """Return full health report as dictionary."""
        return {
            "overall_status": self.get_overall_status(),
            "services": dict(self.results),
            "checked_at": datetime.now().isoformat(),
        }
