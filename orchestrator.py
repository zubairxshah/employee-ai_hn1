"""
Main Orchestrator for AI Personal Employee
Manages all watchers and coordinates their activities
"""

import threading
import time
import logging
from pathlib import Path
import sys
import os

# Add the perception directory to the path so we can import the watchers
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'watchers', 'perception'))

from security_middleware import secure_file_access, audit_log, rate_limit_check, dev_mode_check
from security_config import get_security_config

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class AIPersonalEmployeeOrchestrator:
    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        self.watchers = []
        self.threads = []
        self.security_config = get_security_config()
        
    @secure_file_access
    @audit_log("add_watcher")
    @rate_limit_check("watcher_operations")
    @dev_mode_check
    def add_gmail_watcher(self, credentials_path: str):
        """Add Gmail watcher to the orchestrator"""
        try:
            from watchers.perception.gmail_watcher import GmailWatcher
            watcher = GmailWatcher(str(self.vault_path), credentials_path)
            self.watchers.append(('Gmail', watcher))
            self.security_config.logger.info("Gmail watcher added successfully")
        except ImportError:
            self.security_config.logger.error("Gmail watcher not available - missing dependencies")
            print("Gmail watcher not available - missing dependencies")
        except Exception as e:
            self.security_config.logger.error(f"Error initializing Gmail watcher: {e}")
            print(f"Error initializing Gmail watcher: {e}")

    @secure_file_access
    @audit_log("add_watcher")
    @rate_limit_check("watcher_operations")
    @dev_mode_check
    def add_whatsapp_watcher(self, session_path: str):
        """Add WhatsApp watcher to the orchestrator"""
        try:
            from watchers.perception.whatsapp_watcher import WhatsAppWatcher
            watcher = WhatsAppWatcher(str(self.vault_path), session_path)
            self.watchers.append(('WhatsApp', watcher))
            self.security_config.logger.info("WhatsApp watcher added successfully")
        except ImportError:
            self.security_config.logger.error("WhatsApp watcher not available - missing dependencies")
            print("WhatsApp watcher not available - missing dependencies")
        except Exception as e:
            self.security_config.logger.error(f"Error initializing WhatsApp watcher: {e}")
            print(f"Error initializing WhatsApp watcher: {e}")

    @secure_file_access
    @audit_log("add_watcher")
    @rate_limit_check("watcher_operations")
    @dev_mode_check
    def add_filesystem_watcher(self, drop_folder: str):
        """Add file system watcher to the orchestrator"""
        try:
            from watchers.perception.filesystem_watcher import FileSystemWatcher
            watcher = FileSystemWatcher(str(self.vault_path), drop_folder)
            self.watchers.append(('FileSystem', watcher))
            self.security_config.logger.info("File system watcher added successfully")
        except ImportError:
            self.security_config.logger.error("File system watcher not available - missing dependencies")
            print("File system watcher not available - missing dependencies")
        except Exception as e:
            self.security_config.logger.error(f"Error initializing file system watcher: {e}")
            print(f"Error initializing file system watcher: {e}")

    @audit_log("start_watchers")
    def start_watchers(self):
        """Start all registered watchers in separate threads"""
        for name, watcher in self.watchers:
            if hasattr(watcher, 'run'):
                thread = threading.Thread(target=self._run_watcher, args=(name, watcher), daemon=True)
                thread.start()
                self.threads.append(thread)
                self.security_config.logger.info(f"Started {name} watcher")
                print(f"Started {name} watcher")
            elif hasattr(watcher, 'observer'):  # For filesystem watcher
                thread = threading.Thread(target=watcher.run, daemon=True)
                thread.start()
                self.threads.append(thread)
                self.security_config.logger.info(f"Started {name} watcher")
                print(f"Started {name} watcher")

    def _run_watcher(self, name, watcher):
        """Helper method to run a watcher"""
        try:
            self.security_config.logger.info(f"Running {name} watcher")
            watcher.run()
        except Exception as e:
            self.security_config.logger.error(f"Error in {name} watcher: {e}")
            print(f"Error in {name} watcher: {e}")

    @audit_log("orchestrator_run")
    def run(self):
        """Run the orchestrator"""
        self.security_config.logger.info("Starting AI Personal Employee Orchestrator...")
        print("Starting AI Personal Employee Orchestrator...")
        print(f"Vault path: {self.vault_path}")
        
        # Start all watchers
        self.start_watchers()
        
        print("All watchers started. Press Ctrl+C to stop.")
        
        try:
            # Keep the main thread alive
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.security_config.logger.info("Shutting down AI Personal Employee Orchestrator...")
            print("\nShutting down AI Personal Employee Orchestrator...")
            # Note: The daemon threads will automatically terminate


def main():
    # Initialize the orchestrator
    vault_path = r"D:\prompteng\AI_Employee_Vault"
    orchestrator = AIPersonalEmployeeOrchestrator(vault_path)
    
    # Add watchers (these paths would need to be configured for actual use)
    # orchestrator.add_gmail_watcher(r"D:\prompteng\gmail_credentials.json")
    # orchestrator.add_whatsapp_watcher(r"D:\prompteng\whatsapp_session")
    orchestrator.add_filesystem_watcher(r"D:\prompteng\AI_Employee_Drop")
    
    # Run the orchestrator
    orchestrator.run()


if __name__ == "__main__":
    main()