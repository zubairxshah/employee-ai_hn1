"""
File System Watcher Implementation
Monitors a designated drop folder for new files and creates action files
"""

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path
import shutil
import time
from datetime import datetime


class DropFolderHandler(FileSystemEventHandler):
    def __init__(self, vault_path: str, drop_folder: str):
        self.needs_action = Path(vault_path) / 'Needs_Action'
        self.drop_folder = Path(drop_folder)
        self.processed_files = set()

    def on_created(self, event):
        if event.is_directory:
            return
        
        source = Path(event.src_path)
        if source.suffix.lower() not in ['.pdf', '.docx', '.txt', '.xlsx', '.jpg', '.png']:
            return  # Only process certain file types
            
        if source.name in self.processed_files:
            return  # Skip already processed files
            
        # Create a copy in the needs_action folder
        dest = self.needs_action / f'FILE_{source.name}'
        shutil.copy2(source, dest)
        self.create_metadata(source, dest)
        self.processed_files.add(source.name)

    def create_metadata(self, source: Path, dest: Path):
        meta_path = dest.with_name(f'{dest.stem}_info.md')
        meta_path.write_text(f'''---
type: file_drop
original_name: {source.name}
size: {source.stat().st_size}
created: {datetime.fromtimestamp(source.stat().st_ctime).isoformat()}
modified: {datetime.fromtimestamp(source.stat().st_mtime).isoformat()}
---


New file dropped for processing: {source.name}

## File Details
- Size: {source.stat().st_size} bytes
- Location: {source.parent}
- Created: {datetime.fromtimestamp(source.stat().st_ctime)}
- Modified: {datetime.fromtimestamp(source.stat().st_mtime)}

## Suggested Actions
- [ ] Review file content
- [ ] Determine appropriate action
- [ ] Process according to company handbook
''')

    def on_moved(self, event):
        # Handle file moves if needed
        pass


class FileSystemWatcher:
    def __init__(self, vault_path: str, drop_folder: str):
        self.vault_path = vault_path
        self.drop_folder = drop_folder
        self.handler = DropFolderHandler(vault_path, drop_folder)
        self.observer = Observer()

    def run(self):
        self.observer.schedule(self.handler, str(self.drop_folder), recursive=False)
        self.observer.start()
        print(f"File system watcher started for {self.drop_folder}")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.observer.stop()
            print("File system watcher stopped.")
        
        self.observer.join()


# Example usage
if __name__ == "__main__":
    vault_path = r"D:\prompteng\AI_Employee_Vault"
    drop_folder = r"D:\prompteng\AI_Employee_Drop"  # This would need to be created separately
    
    # Create the drop folder if it doesn't exist
    Path(drop_folder).mkdir(exist_ok=True)
    
    watcher = FileSystemWatcher(vault_path, drop_folder)
    watcher.run()