"""
AI Employee Task Scheduler
Provides flexible scheduling for recurring tasks using APScheduler
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

# Vault path for scheduled task logs
VAULT_PATH = Path(r"D:\prompteng\AI_Employee_Vault")
SCHEDULED_TASKS_LOG = VAULT_PATH / "Scheduled_Tasks" / "execution_log.json"


class TaskScheduler:
    """
    Task Scheduler for AI Employee
    Supports:
    - Cron-based scheduling (e.g., every Monday at 9 AM)
    - Interval-based scheduling (e.g., every 30 minutes)
    - One-time scheduled tasks (e.g., run at specific date/time)
    """
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.tasks = {}
        self._ensure_directories()
        self._load_execution_log()
    
    def _ensure_directories(self):
        """Create necessary directories"""
        SCHEDULED_TASKS_LOG.parent.mkdir(parents=True, exist_ok=True)
    
    def _load_execution_log(self):
        """Load task execution history"""
        if SCHEDULED_TASKS_LOG.exists():
            try:
                with open(SCHEDULED_TASKS_LOG, 'r') as f:
                    self.execution_log = json.load(f)
            except:
                self.execution_log = []
        else:
            self.execution_log = []
    
    def _save_execution_log(self):
        """Save task execution history"""
        with open(SCHEDULED_TASKS_LOG, 'w') as f:
            json.dump(self.execution_log, f, indent=2)
    
    def _log_execution(self, task_name, success, result=""):
        """Log task execution"""
        entry = {
            "task_name": task_name,
            "timestamp": datetime.now().isoformat(),
            "success": success,
            "result": result
        }
        self.execution_log.append(entry)
        self._save_execution_log()
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Executed: {task_name} - {'OK' if success else 'FAIL'}")
    
    def add_cron_task(self, task_name, task_func, args=None, **cron_options):
        """
        Add a recurring task with cron-style scheduling
        
        Args:
            task_name: Unique name for the task
            task_func: Function to execute
            args: Arguments to pass to the function
            cron_options: Cron scheduling options
                - minute: Minute to run (0-59, or *)
                - hour: Hour to run (0-23, or *)
                - day: Day of month (1-31, or *)
                - month: Month (1-12, or *)
                - day_of_week: Day of week (0-6, mon-fri, or *)
        
        Examples:
            # Every day at 9 AM
            scheduler.add_cron_task("daily_post", post_to_linkedin, hour=9, minute=0)
            
            # Every Monday at 10 AM
            scheduler.add_cron_task("weekly_update", send_report, day_of_week='mon', hour=10, minute=0)
            
            # Every 15 minutes
            scheduler.add_cron_task("frequent_check", check_emails, minute='*/15')
        """
        trigger = CronTrigger(**cron_options)
        job = self.scheduler.add_job(
            task_func,
            trigger,
            args=args or [],
            id=task_name,
            name=task_name,
            replace_existing=True
        )
        self.tasks[task_name] = job
        print(f"[OK] Scheduled cron task: {task_name}")
        return job
    
    def add_interval_task(self, task_name, task_func, args=None, **interval_options):
        """
        Add a recurring task with interval-based scheduling
        
        Args:
            task_name: Unique name for the task
            task_func: Function to execute
            args: Arguments to pass to the function
            interval_options: Interval scheduling options
                - seconds: Interval in seconds
                - minutes: Interval in minutes
                - hours: Interval in hours
                - days: Interval in days
        
        Examples:
            # Every 30 minutes
            scheduler.add_interval_task("check_emails", check_new_emails, minutes=30)
            
            # Every hour
            scheduler.add_interval_task("hourly_backup", backup_data, hours=1)
        """
        trigger = IntervalTrigger(**interval_options)
        job = self.scheduler.add_job(
            task_func,
            trigger,
            args=args or [],
            id=task_name,
            name=task_name,
            replace_existing=True
        )
        self.tasks[task_name] = job
        print(f"[OK] Scheduled interval task: {task_name}")
        return job
    
    def add_onetime_task(self, task_name, task_func, run_date, args=None):
        """
        Add a one-time scheduled task
        
        Args:
            task_name: Unique name for the task
            task_func: Function to execute
            run_date: datetime object when to run
            args: Arguments to pass to the function
        
        Examples:
            # Run tomorrow at 2 PM
            from datetime import datetime, timedelta
            tomorrow_2pm = datetime.now().replace(hour=14, minute=0, second=0) + timedelta(days=1)
            scheduler.add_onetime_task("meeting_reminder", send_reminder, tomorrow_2pm)
        """
        trigger = DateTrigger(run_date=run_date)
        job = self.scheduler.add_job(
            task_func,
            trigger,
            args=args or [],
            id=task_name,
            name=task_name,
            replace_existing=True
        )
        self.tasks[task_name] = job
        print(f"[OK] Scheduled one-time task: {task_name} at {run_date}")
        return job
    
    def remove_task(self, task_name):
        """Remove a scheduled task"""
        if task_name in self.tasks:
            self.tasks[task_name].remove()
            del self.tasks[task_name]
            print(f"[OK] Removed task: {task_name}")
    
    def list_tasks(self):
        """List all scheduled tasks"""
        print("\n" + "="*60)
        print("SCHEDULED TASKS")
        print("="*60)
        
        if not self.tasks:
            print("No tasks scheduled")
            return
        
        for name, job in self.tasks.items():
            print(f"\nTask: {name}")
            print(f"  Next run: {job.next_run_time}")
            print(f"  Trigger: {job.trigger}")
        
        print("="*60)
    
    def get_execution_history(self, task_name=None, limit=10):
        """Get task execution history"""
        if task_name:
            history = [e for e in self.execution_log if e['task_name'] == task_name]
        else:
            history = self.execution_log
        
        return history[-limit:]
    
    def start(self):
        """Start the scheduler"""
        self.scheduler.start()
        print("[OK] Task scheduler started")
    
    def shutdown(self, wait=True):
        """Stop the scheduler"""
        self.scheduler.shutdown(wait=wait)
        print("[OK] Task scheduler stopped")


# ============================================================================
# Example Task Functions
# ============================================================================

def post_to_linkedin(message, visibility="PUBLIC"):
    """
    Example: Post a message to LinkedIn
    """
    import requests
    
    try:
        # Load token
        token_file = PROJECT_ROOT / '.linkedin_token.json'
        with open(token_file, 'r') as f:
            token_data = json.load(f)
        
        access_token = token_data['access_token']
        
        # Load config
        env_file = PROJECT_ROOT / '.env'
        person_urn = ""
        with open(env_file, 'r') as f:
            for line in f:
                if 'LINKEDIN_PERSON_URN' in line:
                    person_urn = line.split('=')[1].strip().strip('"')
                    break
        
        # Create post
        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json"
        }
        
        post_data = {
            "author": f"urn:li:person:{person_urn}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": message},
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": visibility
            }
        }
        
        response = requests.post(
            "https://api.linkedin.com/v2/ugcPosts",
            headers=headers,
            json=post_data,
            timeout=30
        )
        
        if response.status_code == 201:
            result = response.json()
            post_id = result.get('id', '')
            return {
                "success": True,
                "post_id": post_id,
                "post_url": f"https://www.linkedin.com/feed/update/{post_id.replace(':', '_')}"
            }
        else:
            return {"success": False, "error": response.text}
            
    except Exception as e:
        return {"success": False, "error": str(e)}


def send_email_report(recipient, subject, body):
    """
    Example: Send an email report via the Gmail API (OAuth2)
    """
    # Imported lazily so scheduler startup does not depend on the email MCP
    from mcp_servers.email_mcp import send_email_gmail_api

    try:
        return send_email_gmail_api(
            to_email=recipient,
            subject=subject,
            body=body
        )
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================================
# Pre-configured Scheduled Tasks
# ============================================================================

def setup_scheduled_tasks(scheduler):
    """
    Set up pre-configured scheduled tasks
    Edit or uncomment tasks you want to enable
    """
    
    # ------------------------------------------------------------------------
    # LINKEDIN POSTING SCHEDULES
    # ------------------------------------------------------------------------
    
    # # Daily motivational post at 9 AM every weekday
    # scheduler.add_cron_task(
    #     "daily_linkedin_post",
    #     lambda: post_to_linkedin("Good morning! Ready to make today count? #MondayMotivation"),
    #     day_of_week='mon-fri',
    #     hour=9,
    #     minute=0
    # )
    
    # # Weekly update every Monday at 10 AM
    # scheduler.add_cron_task(
    #     "weekly_linkedin_update",
    #     lambda: post_to_linkedin("Weekly update: Exciting progress on our AI projects! #WeeklyUpdate #AI"),
    #     day_of_week='mon',
    #     hour=10,
    #     minute=0
    # )
    
    # ------------------------------------------------------------------------
    # EMAIL REPORT SCHEDULES
    # ------------------------------------------------------------------------
    
    # # Daily email digest at 8 AM
    # scheduler.add_cron_task(
    #     "daily_email_digest",
    #     lambda: send_email_report(
    #         "recipient@example.com",
    #         "Daily Digest - AI Employee",
    #         "Here's your daily summary..."
    #     ),
    #     hour=8,
    #     minute=0
    # )
    
    # # Weekly report every Friday at 5 PM
    # scheduler.add_cron_task(
    #     "weekly_report",
    #     lambda: send_email_report(
    #         "recipient@example.com",
    #         "Weekly Report - AI Employee",
    #         "Weekly summary and metrics..."
    #     ),
    #     day_of_week='fri',
    #     hour=17,
    #     minute=0
    # )
    
    # ------------------------------------------------------------------------
    # INTERVAL TASKS
    # ------------------------------------------------------------------------
    
    # # Check for new emails every 15 minutes
    # scheduler.add_interval_task(
    #     "check_new_emails",
    #     lambda: print("Checking for new emails..."),
    #     minutes=15
    # )
    
    # # Backup data every hour
    # scheduler.add_interval_task(
    #     "hourly_backup",
    #     lambda: print("Running hourly backup..."),
    #     hours=1
    # )
    
    print("[OK] Scheduled tasks configured (edit scheduler.py to enable/disable)")


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    print("="*60)
    print("AI Employee Task Scheduler")
    print("="*60)
    
    # Create scheduler
    scheduler = TaskScheduler()
    
    # Set up pre-configured tasks
    setup_scheduled_tasks(scheduler)
    
    # Start scheduler
    scheduler.start()
    
    print("\nScheduler is running. Press Ctrl+C to stop.\n")
    
    try:
        # Keep running
        while True:
            import time
            time.sleep(60)
    except KeyboardInterrupt:
        print("\nShutting down scheduler...")
        scheduler.shutdown()
        print("Scheduler stopped.")
