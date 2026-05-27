"""
Cloud Health Monitor for Platinum Tier
Monitors cloud services (Odoo, MCP servers), writes health reports to Updates/
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

import requests

sys.path.insert(0, str(Path(__file__).parent))

from production_utils import get_structured_logger, MCPClient
from dashboard_manager import DashboardManager
from agent_config import AGENT_ID, get_vault_path


logger = get_structured_logger("cloud_health_monitor")


class CloudHealthMonitor:
    """
    Monitors cloud service health and writes reports to Updates/health_report.md.

    Checks:
    - Odoo ERP availability
    - MCP server health (each server's /health endpoint)
    - Disk usage
    - Memory usage
    """

    def __init__(self, check_interval: int = 300):
        self.check_interval = check_interval
        self.vault_path = Path(get_vault_path())
        self.dashboard = DashboardManager()

        # Odoo doesn't expose /health — probed via the DB selector page (200 = up).
        self.odoo_url = os.getenv("ODOO_URL", "http://localhost:8069")
        self.odoo_timeout = 10

        # MCP services with /health endpoints
        self.services = {
            "email_mcp": MCPClient("http://localhost:8001", "email_mcp", timeout=5),
            "linkedin_mcp": MCPClient("http://localhost:8002", "linkedin_mcp", timeout=5),
            "facebook_mcp": MCPClient("http://localhost:8006", "facebook_mcp", timeout=5),
            "twitter_mcp": MCPClient("http://localhost:8007", "twitter_mcp", timeout=5),
        }

    def _check_odoo(self) -> Dict[str, Any]:
        """Probe Odoo via the DB selector page (Odoo has no /health endpoint)."""
        url = f"{self.odoo_url.rstrip('/')}/web/database/selector"
        try:
            r = requests.get(url, timeout=self.odoo_timeout, allow_redirects=False)
            if r.status_code in (200, 303):
                return {"status": "healthy", "http_status": r.status_code,
                        "checked_at": datetime.now().isoformat()}
            return {"status": "unhealthy", "http_status": r.status_code,
                    "checked_at": datetime.now().isoformat()}
        except requests.RequestException as e:
            return {"status": "unreachable", "error": str(e),
                    "checked_at": datetime.now().isoformat()}

    def check_all(self) -> Dict[str, Any]:
        """Run health checks on all services."""
        results = {}
        overall_healthy = True

        results["odoo"] = self._check_odoo()
        if results["odoo"]["status"] != "healthy":
            overall_healthy = False

        for name, client in self.services.items():
            try:
                health = client.health()
                is_healthy = health.get("status") == "healthy"
                results[name] = {
                    "status": "healthy" if is_healthy else "unhealthy",
                    "response": health,
                    "checked_at": datetime.now().isoformat(),
                }
                if not is_healthy:
                    overall_healthy = False
            except Exception as e:
                results[name] = {
                    "status": "unreachable",
                    "error": str(e),
                    "checked_at": datetime.now().isoformat(),
                }
                overall_healthy = False

        # System checks
        results["system"] = self._check_system()

        report = {
            "overall_status": "healthy" if overall_healthy else "degraded",
            "agent_id": AGENT_ID,
            "checked_at": datetime.now().isoformat(),
            "services": results,
        }

        return report

    def _check_system(self) -> Dict[str, Any]:
        """Check system resources."""
        system_info = {"status": "healthy"}

        try:
            import psutil
            system_info["cpu_percent"] = psutil.cpu_percent(interval=1)
            system_info["memory_percent"] = psutil.virtual_memory().percent
            disk = psutil.disk_usage("/")
            system_info["disk_percent"] = disk.percent

            if system_info["memory_percent"] > 90 or system_info["disk_percent"] > 90:
                system_info["status"] = "warning"
        except ImportError:
            system_info["note"] = "psutil not available"

        return system_info

    def write_health_report(self, report: Dict) -> Path:
        """Write health report to Updates/health_report.md."""
        updates_dir = self.vault_path / "Updates"
        updates_dir.mkdir(parents=True, exist_ok=True)

        report_path = updates_dir / "health_report.md"

        # Build markdown report
        status_emoji = "OK" if report["overall_status"] == "healthy" else "WARNING"
        lines = [
            f"# Health Report [{status_emoji}]",
            f"> Generated: {report['checked_at']}",
            f"> Agent: {report['agent_id']}",
            f"> Overall: **{report['overall_status'].upper()}**",
            "",
            "## Services",
            "| Service | Status |",
            "|---------|--------|",
        ]

        for name, info in report.get("services", {}).items():
            if name == "system":
                continue
            status = info.get("status", "unknown")
            lines.append(f"| {name} | {status} |")

        # System info
        sys_info = report.get("services", {}).get("system", {})
        lines.extend([
            "",
            "## System",
            f"- CPU: {sys_info.get('cpu_percent', 'N/A')}%",
            f"- Memory: {sys_info.get('memory_percent', 'N/A')}%",
            f"- Disk: {sys_info.get('disk_percent', 'N/A')}%",
        ])

        report_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info(f"Health report written: {report['overall_status']}")
        return report_path

    def run(self):
        """Run continuous health monitoring."""
        logger.info(f"Cloud Health Monitor starting (interval: {self.check_interval}s)")

        while True:
            try:
                report = self.check_all()
                self.write_health_report(report)

                # If unhealthy, write a signal for local agent
                if report["overall_status"] != "healthy":
                    unhealthy = [
                        name for name, info in report.get("services", {}).items()
                        if info.get("status") != "healthy" and name != "system"
                    ]
                    self.dashboard.write_signal("health_alert", {
                        "message": f"Services degraded: {', '.join(unhealthy)}",
                        "overall": report["overall_status"],
                        "unhealthy_services": unhealthy,
                    })

                # Also write as dashboard update
                self.dashboard.write_update("health_report", {
                    "summary": f"Health: {report['overall_status']}",
                    "overall": report["overall_status"],
                })

            except Exception as e:
                logger.error(f"Health check cycle error: {e}")

            time.sleep(self.check_interval)


def main():
    check_interval = int(os.getenv("HEALTH_CHECK_INTERVAL", "300"))
    monitor = CloudHealthMonitor(check_interval=check_interval)
    monitor.run()


if __name__ == "__main__":
    main()
