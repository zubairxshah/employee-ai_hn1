"""
File System Watcher for AI Employee
Monitors the Inbox folder for new files and triggers AI processing

FIXED: Only monitors Inbox folder, excludes Approved/Rejected/Done/Needs_Action
"""

import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import subprocess
import json
from datetime import datetime

# Configuration
VAULT_PATH = r"D:\prompteng\AI_Employee_Vault"
INBOX_DIR = os.path.join(VAULT_PATH, "Inbox")
NEEDS_ACTION_DIR = os.path.join(VAULT_PATH, "Needs_Action")
DONE_DIR = os.path.join(VAULT_PATH, "Done")

# Folders to EXCLUDE from monitoring
EXCLUDED_FOLDERS = [
    os.path.join(VAULT_PATH, "Approved"),
    os.path.join(VAULT_PATH, "Rejected"),
    os.path.join(VAULT_PATH, "Done"),
    os.path.join(VAULT_PATH, "Needs_Action"),
    os.path.join(VAULT_PATH, "Pending_Approval"),
    os.path.join(VAULT_PATH, "Logs"),
    os.path.join(VAULT_PATH, ".obsidian"),
]

class VaultHandler(FileSystemEventHandler):
    """Handles file system events in the Obsidian vault"""

    def _is_excluded(self, path):
        """Check if path is in an excluded folder"""
        path_lower = path.lower()
        for excluded in EXCLUDED_FOLDERS:
            if excluded.lower() in path_lower:
                return True
        return False

    def on_created(self, event):
        # Skip if in excluded folder
        if self._is_excluded(event.src_path):
            return
        
        if not event.is_directory and event.src_path.endswith('.md'):
            # Only process files created in Inbox folder
            if INBOX_DIR.lower() in event.src_path.lower():
                print(f"[{datetime.now()}] New file detected in Inbox: {event.src_path}")
                self.process_new_file(event.src_path)
            else:
                print(f"[{datetime.now()}] File created elsewhere (ignored): {event.src_path}")

    def on_modified(self, event):
        # Skip if in excluded folder
        if self._is_excluded(event.src_path):
            return
        
        if not event.is_directory and event.src_path.endswith('.md'):
            print(f"[{datetime.now()}] File modified: {event.src_path}")
            self.process_modified_file(event.src_path)
    
    def process_new_file(self, file_path):
        """Process newly created markdown files from Inbox only"""
        try:
            # Only move files that are actually in Inbox
            if INBOX_DIR.lower() not in file_path.lower():
                print(f"[SKIP] File not in Inbox: {file_path}")
                return
            
            # Move file to Needs_Action directory for processing
            filename = os.path.basename(file_path)
            new_location = os.path.join(NEEDS_ACTION_DIR, filename)

            # Check if file already exists in Needs_Action (avoid overwriting)
            if os.path.exists(new_location):
                print(f"[SKIP] File already exists in Needs_Action: {filename}")
                return

            # Ensure target directory exists
            os.makedirs(NEEDS_ACTION_DIR, exist_ok=True)

            # Move the file
            os.rename(file_path, new_location)
            print(f"[OK] Moved {filename} to Needs_Action for processing")

            # Trigger Claude processing
            self.trigger_claude_processing(new_location)

        except Exception as e:
            print(f"[ERROR] Error processing new file: {str(e)}")
    
    def process_modified_file(self, file_path):
        """Process modified markdown files"""
        try:
            filename = os.path.basename(file_path)
            # Check if file is in Needs_Action (meaning it's being worked on)
            if NEEDS_ACTION_DIR in file_path:
                print(f"{filename} is being actively processed")
            else:
                print(f"{filename} was modified externally")
                
        except Exception as e:
            print(f"Error processing modified file: {str(e)}")
    
    def trigger_claude_processing(self, file_path):
        """Trigger Claude to process the file"""
        try:
            # This would call Claude Code to process the file
            # For now, we'll just log the action
            print(f"Triggering Claude processing for: {file_path}")
            
            # In a real implementation, this would call Claude Code API
            # to analyze and process the content of the file
            
        except Exception as e:
            print(f"Error triggering Claude processing: {str(e)}")

def main():
    """Main function to start the file watcher"""
    print(f"Starting AI Employee File Watcher...")
    print(f"Monitoring: {VAULT_PATH}")
    
    # Ensure required directories exist
    os.makedirs(INBOX_DIR, exist_ok=True)
    os.makedirs(NEEDS_ACTION_DIR, exist_ok=True)
    os.makedirs(DONE_DIR, exist_ok=True)
    
    # Set up the event handler
    event_handler = VaultHandler()
    observer = Observer()
    observer.schedule(event_handler, VAULT_PATH, recursive=True)
    
    # Start the observer
    observer.start()
    print("File watcher started. Monitoring for changes...")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\nStopping file watcher...")
    
    observer.join()
    print("File watcher stopped.")

if __name__ == "__main__":
    main()