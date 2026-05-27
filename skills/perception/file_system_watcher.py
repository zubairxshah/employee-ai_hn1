"""
File System Watcher Skill
Monitors a drop folder for new files and creates action files in the vault
"""

import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import Any, Dict

from .. import AgentSkill


class FileSystemWatcherSkill(AgentSkill):
    """
    Skill for monitoring a file drop folder and processing new files.
    
    Capabilities:
    - Monitors a designated drop folder for new files
    - Filters by file type (pdf, docx, txt, xlsx, images)
    - Creates action files in Needs_Action directory
    - Generates metadata for dropped files
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        config = config or {}
        # Set defaults
        config.setdefault('supported_extensions', ['.pdf', '.docx', '.txt', '.xlsx', '.jpg', '.png', '.jpeg'])
        config.setdefault('processed_files_log', 'processed_files.txt')
        super().__init__(config)
        
        self.processed_files = set()
        self._load_processed_files()
    
    def _load_processed_files(self):
        """Load list of already processed files"""
        log_path = Path(self.config.get('processed_files_log', 'processed_files.txt'))
        if log_path.exists():
            try:
                with open(log_path, 'r') as f:
                    self.processed_files = set(line.strip() for line in f)
            except Exception:
                self.processed_files = set()
    
    def _save_processed_files(self):
        """Save list of processed files"""
        log_path = Path(self.config.get('processed_files_log', 'processed_files.txt'))
        try:
            with open(log_path, 'w') as f:
                for filename in self.processed_files:
                    f.write(f"{filename}\n")
        except Exception as e:
            self.logger.warning(f"Could not save processed files log: {e}")
    
    def validate_inputs(self, parameters: Dict[str, Any]) -> tuple:
        """Validate input parameters"""
        if 'drop_folder' not in parameters:
            return False, "Missing required parameter: drop_folder"
        
        if 'vault_path' not in parameters:
            return False, "Missing required parameter: vault_path"
        
        drop_folder = Path(parameters['drop_folder'])
        if not drop_folder.exists():
            return False, f"Drop folder does not exist: {drop_folder}"
        
        return True, ""
    
    def get_capability_description(self) -> str:
        """Return skill description"""
        return (
            f"File System Watcher Skill (v{self.version}): "
            f"Monitors a drop folder for new files and creates action files in the vault. "
            f"Supported types: {', '.join(self.config.get('supported_extensions', []))}"
        )
    
    def _create_action_file(self, source_path: Path, dest_path: Path) -> Path:
        """Create action file with metadata"""
        # Copy the file
        shutil.copy2(source_path, dest_path)
        
        # Create metadata file
        stat = source_path.stat()
        meta_path = dest_path.with_name(f'{dest_path.stem}_info.md')
        
        metadata = f"""---
type: file_drop
original_name: {source_path.name}
size: {stat.st_size}
created: {datetime.fromtimestamp(stat.st_ctime).isoformat()}
modified: {datetime.fromtimestamp(stat.st_mtime).isoformat()}
processed: {datetime.now().isoformat()}
---


# File Drop for Processing

## Original File
- **Name**: {source_path.name}
- **Size**: {stat.st_size} bytes
- **Source**: {source_path.parent}
- **Created**: {datetime.fromtimestamp(stat.st_ctime)}
- **Modified**: {datetime.fromtimestamp(stat.st_mtime)}

## Suggested Actions
- [ ] Review file content
- [ ] Determine appropriate action
- [ ] Process according to company handbook

## Notes
File was automatically detected and moved for processing.
"""
        
        meta_path.write_text(metadata, encoding='utf-8')
        return meta_path
    
    def execute(self, context: Dict[str, Any], parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the file system watcher skill.
        
        Parameters:
        - drop_folder: Path to the drop folder to monitor
        - vault_path: Path to the Obsidian vault
        - scan: If True, scan immediately; if False, return watcher info
        
        Returns:
        - Dictionary with scan results or watcher information
        """
        drop_folder = Path(parameters['drop_folder'])
        vault_path = Path(parameters['vault_path'])
        scan = parameters.get('scan', True)
        
        needs_action_dir = vault_path / 'Needs_Action'
        needs_action_dir.mkdir(parents=True, exist_ok=True)
        
        if not scan:
            # Return watcher info without scanning
            return {
                "success": True,
                "watcher_info": {
                    "drop_folder": str(drop_folder),
                    "vault_path": str(vault_path),
                    "supported_extensions": self.config.get('supported_extensions', []),
                    "processed_count": len(self.processed_files)
                }
            }
        
        # Scan for new files
        new_files = []
        processed_count = 0
        
        for file_path in drop_folder.iterdir():
            if file_path.is_dir():
                continue
            
            # Check extension
            if file_path.suffix.lower() not in self.config.get('supported_extensions', []):
                continue
            
            # Check if already processed
            if file_path.name in self.processed_files:
                continue
            
            # Process the file
            try:
                dest_name = f'FILE_{file_path.name}'
                dest_path = needs_action_dir / dest_name
                
                # Create action file
                meta_path = self._create_action_file(file_path, dest_path)
                
                # Mark as processed
                self.processed_files.add(file_path.name)
                self._save_processed_files()
                
                new_files.append({
                    "original": str(file_path),
                    "action_file": str(dest_path),
                    "metadata_file": str(meta_path)
                })
                processed_count += 1
                
                self.logger.info(f"Processed file drop: {file_path.name}")
                
            except Exception as e:
                self.logger.error(f"Error processing file {file_path.name}: {e}")
        
        return {
            "success": True,
            "files_processed": processed_count,
            "new_files": new_files,
            "total_processed_all_time": len(self.processed_files)
        }


# Auto-register the skill when module is imported
def _register():
    from ..registry import register_skill
    register_skill(FileSystemWatcherSkill, "file_system_watcher")

_register()
