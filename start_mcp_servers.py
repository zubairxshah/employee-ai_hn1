"""
MCP Server Launcher
Starts all MCP servers for the AI Personal Employee system
"""

import subprocess
import sys
import time
import os
from pathlib import Path

# Project root directory
PROJECT_ROOT = Path(__file__).parent.absolute()
MCP_SERVERS_DIR = PROJECT_ROOT / "mcp_servers"


def start_server(name, script_path, port):
    """Start an MCP server as a background process"""
    print(f"Starting {name} server on port {port}...")
    
    # Start the server with the project root in PYTHONPATH
    env = os.environ.copy()
    pythonpath = str(PROJECT_ROOT)
    if 'PYTHONPATH' in env:
        pythonpath = f"{PROJECT_ROOT}{os.pathsep}{env['PYTHONPATH']}"
    env['PYTHONPATH'] = pythonpath
    
    # Start the server as a background process
    process = subprocess.Popen(
        [sys.executable, str(script_path)],
        cwd=str(PROJECT_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Give the server time to start
    time.sleep(2)
    
    # Check if the process is still running
    if process.poll() is None:
        print(f"[OK] {name} server started successfully (PID: {process.pid})")
        return process
    else:
        stdout, stderr = process.communicate()
        print(f"[FAIL] {name} server failed to start")
        if stderr:
            print(f"  Error: {stderr.decode()}")
        return None


def main():
    print("=" * 60)
    print("AI Personal Employee - MCP Server Launcher")
    print("=" * 60)
    
    processes = []
    
    # Start Filesystem MCP Server (port 8000)
    fs_process = start_server(
        "Filesystem MCP",
        MCP_SERVERS_DIR / "filesystem_mcp.py",
        8000
    )
    if fs_process:
        processes.append(("filesystem", fs_process))

    # Start Email MCP Server (port 8001)
    email_process = start_server(
        "Email MCP",
        MCP_SERVERS_DIR / "email_mcp.py",
        8001
    )
    if email_process:
        processes.append(("email", email_process))

    # Start LinkedIn MCP Server (port 8002)
    linkedin_process = start_server(
        "LinkedIn MCP",
        MCP_SERVERS_DIR / "linkedin_mcp.py",
        8002
    )
    if linkedin_process:
        processes.append(("linkedin", linkedin_process))

    # Start Approval MCP Server (port 8003)
    approval_process = start_server(
        "Approval MCP",
        MCP_SERVERS_DIR / "approval_mcp.py",
        8003
    )
    if approval_process:
        processes.append(("approval", approval_process))

    # Start WhatsApp MCP Server (port 8004)
    whatsapp_process = start_server(
        "WhatsApp MCP",
        MCP_SERVERS_DIR / "whatsapp_mcp.py",
        8004
    )
    if whatsapp_process:
        processes.append(("whatsapp", whatsapp_process))

    # Start Odoo MCP Server (port 8005) - Gold Tier
    odoo_process = start_server(
        "Odoo MCP",
        MCP_SERVERS_DIR / "odoo_mcp.py",
        8005
    )
    if odoo_process:
        processes.append(("odoo", odoo_process))

    # Start Facebook/Instagram MCP Server (port 8006) - Gold Tier
    facebook_process = start_server(
        "Facebook MCP",
        MCP_SERVERS_DIR / "facebook_mcp.py",
        8006
    )
    if facebook_process:
        processes.append(("facebook", facebook_process))

    # Start Twitter (X) MCP Server (port 8007) - Gold Tier
    twitter_process = start_server(
        "Twitter MCP",
        MCP_SERVERS_DIR / "twitter_mcp.py",
        8007
    )
    if twitter_process:
        processes.append(("twitter", twitter_process))

    print("\n" + "=" * 60)
    if processes:
        print(f"Successfully started {len(processes)} MCP server(s)")
        print("\nServer URLs:")
        port_map = {"filesystem": 8000, "email": 8001, "linkedin": 8002, "approval": 8003, "whatsapp": 8004, "odoo": 8005, "facebook": 8006, "twitter": 8007}
        for name, proc in processes:
            print(f"  - {name}: http://localhost:{port_map.get(name, 8000)}")
        print("\nPress Ctrl+C to stop all servers")
        print("=" * 60)
        
        # Keep the script running
        try:
            while True:
                time.sleep(1)
                # Check if processes are still running
                for name, proc in processes[:]:
                    if proc.poll() is not None:
                        print(f"[FAIL] {name} server has stopped")
                        processes.remove((name, proc))
                        if not processes:
                            print("All servers stopped. Exiting.")
                            return
        except KeyboardInterrupt:
            print("\nShutting down all MCP servers...")
            for name, proc in processes:
                proc.terminate()
            print("All servers stopped.")
    else:
        print("Failed to start any MCP servers")
        sys.exit(1)


if __name__ == "__main__":
    main()
