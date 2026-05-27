"""
Cloud MCP Server Launcher
Starts only cloud-appropriate MCP servers (no WhatsApp MCP, no Approval executor).
"""

import subprocess
import sys
import time
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.absolute()
MCP_SERVERS_DIR = PROJECT_ROOT / "mcp_servers"


def start_server(name, script_path, port):
    """Start an MCP server as a background process"""
    print(f"Starting {name} server on port {port}...")

    env = os.environ.copy()
    pythonpath = str(PROJECT_ROOT)
    if 'PYTHONPATH' in env:
        pythonpath = f"{PROJECT_ROOT}{os.pathsep}{env['PYTHONPATH']}"
    env['PYTHONPATH'] = pythonpath

    # Ensure AGENT_ROLE=cloud is passed
    env['AGENT_ROLE'] = 'cloud'

    process = subprocess.Popen(
        [sys.executable, str(script_path)],
        cwd=str(PROJECT_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    time.sleep(2)

    if process.poll() is None:
        print(f"[OK] {name} server started (PID: {process.pid})")
        return process
    else:
        stdout, stderr = process.communicate()
        print(f"[FAIL] {name} server failed to start")
        if stderr:
            print(f"  Error: {stderr.decode()}")
        return None


def main():
    print("=" * 60)
    print("AI Employee - Cloud MCP Server Launcher")
    print("=" * 60)
    print("Cloud mode: Only starting read/draft-capable servers")
    print("Excluded: WhatsApp MCP (8004), Approval MCP (8003)")
    print("=" * 60)

    processes = []

    # Filesystem MCP (port 8000) - needed for vault operations
    p = start_server("Filesystem MCP", MCP_SERVERS_DIR / "filesystem_mcp.py", 8000)
    if p: processes.append(("filesystem", p))

    # Email MCP (port 8001) - draft-only on cloud
    p = start_server("Email MCP", MCP_SERVERS_DIR / "email_mcp.py", 8001)
    if p: processes.append(("email", p))

    # LinkedIn MCP (port 8002) - read + draft
    p = start_server("LinkedIn MCP", MCP_SERVERS_DIR / "linkedin_mcp.py", 8002)
    if p: processes.append(("linkedin", p))

    # Skip Approval MCP (8003) - Local only
    # Skip WhatsApp MCP (8004) - Local only

    # Odoo MCP (port 8005) - read + draft on cloud
    p = start_server("Odoo MCP", MCP_SERVERS_DIR / "odoo_mcp.py", 8005)
    if p: processes.append(("odoo", p))

    # Facebook MCP (port 8006) - read + draft
    p = start_server("Facebook MCP", MCP_SERVERS_DIR / "facebook_mcp.py", 8006)
    if p: processes.append(("facebook", p))

    # Twitter MCP (port 8007) - read + draft
    p = start_server("Twitter MCP", MCP_SERVERS_DIR / "twitter_mcp.py", 8007)
    if p: processes.append(("twitter", p))

    print(f"\n{'=' * 60}")
    if processes:
        print(f"Started {len(processes)} cloud MCP server(s)")
        port_map = {
            "filesystem": 8000, "email": 8001, "linkedin": 8002,
            "odoo": 8005, "facebook": 8006, "twitter": 8007,
        }
        for name, proc in processes:
            print(f"  - {name}: http://localhost:{port_map.get(name, '?')}")
        print("\nPress Ctrl+C to stop all servers")
        print("=" * 60)

        try:
            while True:
                time.sleep(1)
                for name, proc in processes[:]:
                    if proc.poll() is not None:
                        print(f"[FAIL] {name} server stopped")
                        processes.remove((name, proc))
                        if not processes:
                            print("All servers stopped.")
                            return
        except KeyboardInterrupt:
            print("\nShutting down cloud MCP servers...")
            for name, proc in processes:
                proc.terminate()
            print("All servers stopped.")
    else:
        print("Failed to start any MCP servers")
        sys.exit(1)


if __name__ == "__main__":
    main()
