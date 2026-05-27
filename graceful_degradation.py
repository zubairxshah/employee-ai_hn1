"""
Graceful Degradation for AI Personal Employee
Handles system failures and degrades functionality gracefully
"""

import os
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import json
import shutil


class GracefulDegradationManager:
    """Manages graceful degradation when components fail"""
    
    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        self.temp_dir = self.vault_path / "Temp"
        self.quarantine_dir = self.vault_path / "Quarantine"
        self.queue_dir = self.vault_path / "Queue"
        
        # Create necessary directories
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger('GracefulDegradation')
    
    def handle_gmail_failure(self, email_data: Dict[str, Any]) -> bool:
        """
        Handle Gmail API failure by queuing emails locally
        
        Args:
            email_data: Dictionary containing email information
            
        Returns:
            bool: True if successfully queued, False otherwise
        """
        try:
            # Create a timestamped filename for the queued email
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
            filename = f"queued_email_{timestamp}.json"
            filepath = self.queue_dir / filename
            
            # Save the email data to be processed later
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(email_data, f, indent=2, default=str)
            
            self.logger.info(f"Gmail API down, email queued: {filepath}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to queue email during Gmail failure: {e}")
            return False
    
    def handle_banking_failure(self, payment_data: Dict[str, Any]) -> bool:
        """
        Handle banking API timeout by requiring fresh approval
        
        Args:
            payment_data: Dictionary containing payment information
            
        Returns:
            bool: Always returns False to prevent automatic retries
        """
        try:
            # Never retry payments automatically, always require fresh approval
            # Move to a special pending approval queue
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
            filename = f"payment_hold_{timestamp}.json"
            filepath = self.queue_dir / "Payment_Holds" / filename
            
            # Ensure the payment holds directory exists
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            # Add reason for hold
            payment_data['hold_reason'] = 'Banking API timeout - requires fresh approval'
            payment_data['hold_timestamp'] = datetime.now().isoformat()
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(payment_data, f, indent=2, default=str)
            
            self.logger.warning(f"Banking API timeout, payment held for approval: {filepath}")
            return False  # Never retry automatically
        except Exception as e:
            self.logger.error(f"Failed to hold payment during banking failure: {e}")
            return False
    
    def handle_claude_unavailable(self, task_data: Dict[str, Any]) -> bool:
        """
        Handle Claude Code unavailability by queuing tasks
        
        Args:
            task_data: Dictionary containing task information
            
        Returns:
            bool: True if successfully queued, False otherwise
        """
        try:
            # Add to general processing queue
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
            filename = f"queued_task_{timestamp}.json"
            filepath = self.queue_dir / "Claude_Queued" / filename
            
            # Ensure the Claude queue directory exists
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            # Add queue timestamp
            task_data['queue_timestamp'] = datetime.now().isoformat()
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(task_data, f, indent=2, default=str)
            
            self.logger.info(f"Claude unavailable, task queued: {filepath}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to queue task during Claude unavailability: {e}")
            return False
    
    def handle_vault_locked(self, file_path: str, content: str) -> bool:
        """
        Handle Obsidian vault lock by writing to temporary folder
        
        Args:
            file_path: Original path where file should be written
            content: Content to write to the file
            
        Returns:
            bool: True if successfully written to temp, False otherwise
        """
        try:
            # Create a temporary file with the same name structure
            original_path = Path(file_path)
            temp_filename = f"temp_{original_path.name}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
            temp_filepath = self.temp_dir / temp_filename
            
            with open(temp_filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Store metadata about the original location
            meta_filepath = temp_filepath.with_suffix('.meta.json')
            meta_data = {
                'original_path': str(original_path),
                'temp_creation_time': datetime.now().isoformat(),
                'sync_attempted': False
            }
            
            with open(meta_filepath, 'w', encoding='utf-8') as f:
                json.dump(meta_data, f, indent=2)
            
            self.logger.warning(f"Vault locked, file written to temp: {temp_filepath}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to write to temp during vault lock: {e}")
            return False
    
    def sync_temp_to_vault(self) -> bool:
        """
        Sync temporary files back to the vault when available
        
        Returns:
            bool: True if sync successful, False otherwise
        """
        try:
            synced_count = 0
            for meta_file in self.temp_dir.glob('*.meta.json'):
                with open(meta_file, 'r', encoding='utf-8') as f:
                    meta_data = json.load(f)
                
                if meta_data.get('sync_attempted', False):
                    continue  # Already attempted sync
                
                temp_file = meta_file.with_suffix('')
                original_path = Path(meta_data['original_path'])
                
                # Attempt to write to the original location
                try:
                    # Ensure parent directory exists
                    original_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Read temp content and write to original location
                    with open(temp_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    with open(original_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    # Mark as synced in metadata
                    meta_data['sync_attempted'] = True
                    meta_data['sync_time'] = datetime.now().isoformat()
                    
                    with open(meta_file, 'w', encoding='utf-8') as f:
                        json.dump(meta_data, f, indent=2)
                    
                    # Clean up temp files
                    temp_file.unlink()
                    
                    synced_count += 1
                    self.logger.info(f"Synced temp file to vault: {original_path}")
                    
                except Exception as e:
                    self.logger.error(f"Failed to sync temp file {temp_file} to {original_path}: {e}")
            
            self.logger.info(f"Synced {synced_count} temp files to vault")
            return True
            
        except Exception as e:
            self.logger.error(f"Error during temp to vault sync: {e}")
            return False
    
    def quarantine_corrupted_data(self, file_path: str, reason: str) -> bool:
        """
        Quarantine corrupted or problematic data
        
        Args:
            file_path: Path to the file to quarantine
            reason: Reason for quarantining
            
        Returns:
            bool: True if successfully quarantined, False otherwise
        """
        try:
            original_path = Path(file_path)
            quarantine_filename = f"quarantine_{original_path.name}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
            quarantine_path = self.quarantine_dir / quarantine_filename
            
            # Copy the file to quarantine
            shutil.copy2(original_path, quarantine_path)
            
            # Create quarantine metadata
            meta_path = quarantine_path.with_suffix('.meta.json')
            meta_data = {
                'original_path': str(original_path),
                'quarantine_time': datetime.now().isoformat(),
                'reason': reason,
                'review_status': 'pending'
            }
            
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(meta_data, f, indent=2)
            
            self.logger.error(f"Quarantined problematic file: {quarantine_path} (reason: {reason})")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to quarantine file {file_path}: {e}")
            return False
    
    def process_queues(self) -> Dict[str, int]:
        """
        Process all queues to catch up on pending work
        
        Returns:
            Dict with counts of processed items by queue type
        """
        results = {
            'email_queue_processed': 0,
            'claude_queue_processed': 0,
            'payment_holds_processed': 0,
            'errors': 0
        }
        
        try:
            # Process email queue
            for email_file in (self.queue_dir).glob('queued_email_*.json'):
                try:
                    with open(email_file, 'r', encoding='utf-8') as f:
                        email_data = json.load(f)
                    
                    # In a real implementation, this would attempt to send the email
                    # For now, we'll just log it
                    self.logger.info(f"Would process queued email: {email_data.get('subject', 'Unknown')}")
                    
                    # Remove the processed file
                    email_file.unlink()
                    results['email_queue_processed'] += 1
                    
                except Exception as e:
                    self.logger.error(f"Error processing queued email {email_file}: {e}")
                    results['errors'] += 1
            
            # Process Claude queue
            claude_queue_dir = self.queue_dir / "Claude_Queued"
            if claude_queue_dir.exists():
                for task_file in claude_queue_dir.glob('queued_task_*.json'):
                    try:
                        with open(task_file, 'r', encoding='utf-8') as f:
                            task_data = json.load(f)
                        
                        # In a real implementation, this would submit the task to Claude
                        self.logger.info(f"Would process queued task: {task_data.get('description', 'Unknown')}")
                        
                        # Remove the processed file
                        task_file.unlink()
                        results['claude_queue_processed'] += 1
                        
                    except Exception as e:
                        self.logger.error(f"Error processing queued task {task_file}: {e}")
                        results['errors'] += 1
            
            # Process payment holds (would require human approval in real system)
            payment_holds_dir = self.queue_dir / "Payment_Holds"
            if payment_holds_dir.exists():
                for payment_file in payment_holds_dir.glob('payment_hold_*.json'):
                    try:
                        with open(payment_file, 'r', encoding='utf-8') as f:
                            payment_data = json.load(f)
                        
                        self.logger.info(f"Payment on hold requires approval: {payment_data.get('description', 'Unknown')}")
                        results['payment_holds_processed'] += 1
                        
                    except Exception as e:
                        self.logger.error(f"Error processing payment hold {payment_file}: {e}")
                        results['errors'] += 1
            
            self.logger.info(f"Queue processing results: {results}")
            return results
            
        except Exception as e:
            self.logger.error(f"Error during queue processing: {e}")
            results['errors'] += 1
            return results


# Global instance
degradation_manager = GracefulDegradationManager(r"D:\prompteng\AI_Employee_Vault")


def get_degradation_manager() -> GracefulDegradationManager:
    """Get the global degradation manager instance"""
    return degradation_manager