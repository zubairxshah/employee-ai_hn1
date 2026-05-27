"""
Watchdog Process for AI Personal Employee
Monitors and restarts critical processes
"""

import os
import subprocess
import time
import psutil
import logging
import json
import threading
from pathlib import Path
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
import signal
import sys
from typing import Dict, List, Optional


class Watchdog:
    """Monitors and manages critical processes for the AI Employee"""

    # Cloud-specific processes (no WhatsApp, no approval executor)
    CLOUD_PROCESSES = {
        'cloud_orchestrator': {
            'command': ['python', 'cloud_orchestrator.py'],
            'restart_on_failure': True,
            'max_restarts_per_hour': 5
        },
        'cloud_health_monitor': {
            'command': ['python', 'cloud_health_monitor.py'],
            'restart_on_failure': True,
            'max_restarts_per_hour': 3
        },
    }

    LOCAL_PROCESSES = {
        'orchestrator': {
            'command': ['python', 'orchestrator.py'],
            'restart_on_failure': True,
            'max_restarts_per_hour': 5
        },
        'scheduler': {
            'command': ['python', 'scheduler.py'],
            'restart_on_failure': True,
            'max_restarts_per_hour': 3
        },
        'filesystem_mcp': {
            'command': ['python', 'mcp_servers', 'filesystem_mcp.py'],
            'restart_on_failure': True,
            'max_restarts_per_hour': 3
        },
        'approval_mcp': {
            'command': ['python', 'mcp_servers', 'approval_mcp.py'],
            'restart_on_failure': True,
            'max_restarts_per_hour': 3
        },
    }

    def __init__(self, config_path: str = "watchdog_config.json", cloud_mode: bool = False):
        self.config_path = Path(config_path)
        self.processes: Dict[str, subprocess.Popen] = {}
        self.pid_files: Dict[str, Path] = {}
        self.logger = self._setup_logger()
        self.running = True
        self.cloud_mode = cloud_mode or os.environ.get("AGENT_ROLE", "").lower() == "cloud"
        self.health_server = None

        # Define critical processes based on mode
        if self.cloud_mode:
            self.critical_processes = dict(self.CLOUD_PROCESSES)
        else:
            self.critical_processes = dict(self.LOCAL_PROCESSES)
        
        # Track restart history
        self.restart_history: Dict[str, List[datetime]] = {name: [] for name in self.critical_processes}
        
        # Load or create config
        self.load_config()
    
    def _setup_logger(self):
        """Set up the watchdog logger"""
        logger = logging.getLogger('Watchdog')
        logger.setLevel(logging.INFO)
        
        # Create file handler
        handler = logging.FileHandler('watchdog.log')
        handler.setLevel(logging.INFO)
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def load_config(self):
        """Load watchdog configuration"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                self.critical_processes.update(config.get('processes', {}))
            except Exception as e:
                self.logger.error(f"Error loading watchdog config: {e}")
        else:
            # Create default config
            config = {
                'processes': self.critical_processes,
                'check_interval': 60,
                'alert_on_restart': True
            }
            self.save_config(config)
    
    def save_config(self, config: dict):
        """Save watchdog configuration"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"Error saving watchdog config: {e}")
    
    def is_process_running(self, process_name: str) -> bool:
        """Check if a process is running"""
        if process_name in self.processes:
            proc = self.processes[process_name]
            # Check if the process is still alive
            try:
                # Use psutil to check if the PID is still running
                if proc.poll() is None:  # Process is still running
                    return True
                else:  # Process has terminated
                    return False
            except:
                return False
        return False
    
    def get_pid_file_path(self, process_name: str) -> Path:
        """Get the PID file path for a process"""
        return Path(f'/tmp/{process_name}.pid')  # Using temp directory for PID files
    
    def start_process(self, process_name: str) -> bool:
        """Start a critical process"""
        try:
            if process_name not in self.critical_processes:
                self.logger.error(f"Unknown process: {process_name}")
                return False
            
            process_config = self.critical_processes[process_name]
            command = process_config['command']
            
            # Check restart limits
            if not self.check_restart_limit(process_name):
                self.logger.warning(f"Restart limit exceeded for {process_name}, not restarting")
                return False
            
            # Get working directory if specified
            cwd = process_config.get('working_directory', '.')
            
            # Start the process
            proc = subprocess.Popen(command, cwd=cwd)
            
            self.processes[process_name] = proc
            pid_file = self.get_pid_file_path(process_name)
            pid_file.write_text(str(proc.pid))
            self.pid_files[process_name] = pid_file
            
            self.logger.info(f"Started {process_name} with PID {proc.pid} in {cwd}")
            
            # Record restart
            self.record_restart(process_name)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting {process_name}: {e}")
            return False
    
    def stop_process(self, process_name: str) -> bool:
        """Stop a critical process"""
        try:
            if process_name in self.processes:
                proc = self.processes[process_name]
                proc.terminate()
                
                # Wait a bit for graceful shutdown
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Force kill if it doesn't shut down gracefully
                    proc.kill()
                    proc.wait()
                
                # Remove PID file
                if process_name in self.pid_files:
                    pid_file = self.pid_files[process_name]
                    if pid_file.exists():
                        pid_file.unlink()
                
                del self.processes[process_name]
                self.logger.info(f"Stopped {process_name}")
                return True
            else:
                self.logger.warning(f"Process {process_name} not found in managed processes")
                return False
                
        except Exception as e:
            self.logger.error(f"Error stopping {process_name}: {e}")
            return False
    
    def check_restart_limit(self, process_name: str) -> bool:
        """Check if restart limit is exceeded for a process"""
        if process_name not in self.restart_history:
            return True
        
        # Get restarts in the last hour
        one_hour_ago = datetime.now() - timedelta(hours=1)
        recent_restarts = [dt for dt in self.restart_history[process_name] if dt > one_hour_ago]
        
        max_restarts = self.critical_processes[process_name].get('max_restarts_per_hour', 5)
        return len(recent_restarts) < max_restarts
    
    def record_restart(self, process_name: str):
        """Record a restart event"""
        if process_name not in self.restart_history:
            self.restart_history[process_name] = []
        
        self.restart_history[process_name].append(datetime.now())
        
        # Keep only recent restarts (last hour)
        one_hour_ago = datetime.now() - timedelta(hours=1)
        self.restart_history[process_name] = [
            dt for dt in self.restart_history[process_name] if dt > one_hour_ago
        ]
    
    def notify_human(self, message: str):
        """Notify human operator of an issue"""
        self.logger.critical(f"ALERT: {message}")
        # In a real implementation, this might send an email, SMS, or other notification
        # For now, we'll just log it as critical
    
    def check_and_restart(self):
        """Check all processes and restart any that have failed"""
        for name, config in self.critical_processes.items():
            if not self.is_process_running(name):
                if config.get('restart_on_failure', True):
                    self.logger.warning(f'{name} not running, restarting...')
                    success = self.start_process(name)
                    if success:
                        self.notify_human(f'{name} was restarted after failure')
                    else:
                        self.logger.error(f'Failed to restart {name}')
                else:
                    self.logger.warning(f'{name} not running but restart disabled')
    
    def cleanup(self):
        """Clean up resources before shutdown"""
        self.logger.info("Watchdog shutting down, stopping all managed processes...")
        for process_name in list(self.processes.keys()):
            self.stop_process(process_name)
        self.running = False
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, initiating shutdown...")
        self.cleanup()
        sys.exit(0)
    
    def _start_health_server(self, port: int = 9000):
        """Start an HTTP health endpoint for Docker healthcheck."""
        watchdog = self

        class HealthHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/health":
                    running = list(watchdog.processes.keys())
                    body = json.dumps({
                        "status": "healthy",
                        "mode": "cloud" if watchdog.cloud_mode else "local",
                        "managed_processes": running,
                        "timestamp": datetime.now().isoformat(),
                    })
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(body.encode())
                else:
                    self.send_response(404)
                    self.end_headers()

            def log_message(self, format, *args):
                pass  # Suppress access logs

        try:
            server = HTTPServer(("0.0.0.0", port), HealthHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            self.health_server = server
            self.logger.info(f"Health endpoint started on port {port}")
        except Exception as e:
            self.logger.warning(f"Could not start health server on port {port}: {e}")

    def run(self, check_interval: int = 60):
        """Run the watchdog continuously"""
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        self.logger.info(f"Watchdog started (mode: {'cloud' if self.cloud_mode else 'local'})")

        # Start health endpoint (port 9000 for Docker healthcheck)
        if self.cloud_mode:
            self._start_health_server(port=9000)

        # Start all critical processes initially
        for process_name in self.critical_processes:
            if not self.is_process_running(process_name):
                self.start_process(process_name)

        try:
            while self.running:
                self.check_and_restart()
                time.sleep(check_interval)
        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt received, shutting down...")
        except Exception as e:
            self.logger.error(f"Unexpected error in watchdog: {e}")
        finally:
            self.cleanup()


def main():
    """Main function to run the watchdog"""
    from datetime import timedelta  # Import here to avoid conflicts
    
    watchdog = Watchdog()
    # Run with 60-second intervals as specified in the requirements
    watchdog.run(check_interval=60)


if __name__ == "__main__":
    main()