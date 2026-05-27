"""
Windows Task Scheduler Integration for AI Employee
Creates and manages scheduled tasks in Windows Task Scheduler
"""

import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime, timedelta
import getpass

# Project root
PROJECT_ROOT = Path(__file__).parent.absolute()
PYTHON_EXE = sys.executable
SCHEDULER_SCRIPT = PROJECT_ROOT / "scheduler.py"
TASK_NAME_PREFIX = "AI_Employee_"


class WindowsTaskScheduler:
    """
    Windows Task Scheduler Integration
    Creates scheduled tasks that run even when the app is closed
    """
    
    def __init__(self):
        self.username = getpass.getuser()
        self.tasks = []
    
    def create_task(self, task_name, script_path, trigger_type, **trigger_args):
        """
        Create a scheduled task in Windows Task Scheduler
        
        Args:
            task_name: Name for the task
            script_path: Path to Python script to run
            trigger_type: 'daily', 'weekly', 'hourly', 'at_startup', 'on_idle'
            trigger_args: Trigger-specific arguments
                - For daily: hour=9, minute=0
                - For weekly: day_of_week='MON', hour=10, minute=0
                - For hourly: interval=1 (hours)
        """
        full_task_name = f"{TASK_NAME_PREFIX}{task_name}"
        
        # Build schtasks command
        cmd = [
            "schtasks", "/Create",
            "/TN", full_task_name,
            "/TR", f'"{PYTHON_EXE}" "{script_path}"',
            "/RL", "HIGHEST",
            "/F"  # Force create (overwrite if exists)
        ]
        
        # Add trigger
        if trigger_type == "daily":
            hour = trigger_args.get('hour', 9)
            minute = trigger_args.get('minute', 0)
            cmd.extend(["/SC", "DAILY", "/ST", f"{hour:02d}:{minute:02d}"])
        
        elif trigger_type == "weekly":
            day_map = {
                'MON': 'MONDAY',
                'TUE': 'TUESDAY',
                'WED': 'WEDNESDAY',
                'THU': 'THURSDAY',
                'FRI': 'FRIDAY',
                'SAT': 'SATURDAY',
                'SUN': 'SUNDAY'
            }
            day = trigger_args.get('day_of_week', 'MON')
            day_full = day_map.get(day.upper(), 'MONDAY')
            hour = trigger_args.get('hour', 9)
            minute = trigger_args.get('minute', 0)
            cmd.extend(["/SC", "WEEKLY", "/D", day_full, "/ST", f"{hour:02d}:{minute:02d}"])
        
        elif trigger_type == "hourly":
            interval = trigger_args.get('interval', 1)
            cmd.extend(["/SC", "HOURLY", "/MO", str(interval)])
        
        elif trigger_type == "at_startup":
            cmd.extend(["/SC", "ONSTART"])
        
        elif trigger_type == "on_idle":
            cmd.extend(["/SC", "ONIDLE"])
        
        elif trigger_type == "once":
            # One-time task
            run_time = trigger_args.get('run_time')
            if run_time:
                cmd.extend(["/SC", "ONCE", "/ST", run_time.strftime("%H:%M"), "/SD", run_time.strftime("%m/%d/%Y")])
        
        # Execute command
        print(f"Creating task: {full_task_name}")
        print(f"Command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"[OK] Task created successfully: {full_task_name}")
            self.tasks.append(full_task_name)
            return True
        else:
            print(f"[FAIL] Failed to create task")
            print(f"Error: {result.stderr}")
            return False
    
    def delete_task(self, task_name):
        """Delete a scheduled task"""
        full_task_name = f"{TASK_NAME_PREFIX}{task_name}"
        cmd = ["schtasks", "/Delete", "/TN", full_task_name, "/F"]
        
        print(f"Deleting task: {full_task_name}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"[OK] Task deleted: {full_task_name}")
            return True
        else:
            print(f"[FAIL] Failed to delete task")
            print(f"Error: {result.stderr}")
            return False
    
    def list_tasks(self):
        """List all AI Employee scheduled tasks"""
        print("\n" + "="*60)
        print("AI EMPLOYEE SCHEDULED TASKS")
        print("="*60)
        
        # Query all tasks
        cmd = ["schtasks", "/Query", "/FO", "LIST", "/V"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            found_tasks = []
            
            for line in lines:
                if TASK_NAME_PREFIX in line:
                    found_tasks.append(line.strip())
            
            if found_tasks:
                print("\nFound tasks:")
                for task in found_tasks:
                    print(f"  - {task}")
            else:
                print("\nNo AI Employee tasks found")
            
            return found_tasks
        else:
            print(f"[FAIL] Failed to list tasks")
            return []
    
    def run_task_now(self, task_name):
        """Run a scheduled task immediately"""
        full_task_name = f"{TASK_NAME_PREFIX}{task_name}"
        cmd = ["schtasks", "/Run", "/TN", full_task_name]
        
        print(f"Running task: {full_task_name}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"[OK] Task triggered: {full_task_name}")
            return True
        else:
            print(f"[FAIL] Failed to run task")
            print(f"Error: {result.stderr}")
            return False
    
    def get_task_info(self, task_name):
        """Get detailed information about a task"""
        full_task_name = f"{TASK_NAME_PREFIX}{task_name}"
        cmd = ["schtasks", "/Query", "/TN", full_task_name, "/FO", "LIST", "/V"]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"\nTask Info: {full_task_name}")
            print(result.stdout)
            return result.stdout
        else:
            print(f"[FAIL] Failed to get task info")
            return None


# ============================================================================
# Pre-configured Task Templates
# ============================================================================

def setup_common_tasks():
    """
    Set up common scheduled tasks
    Uncomment tasks you want to enable
    """
    scheduler = WindowsTaskScheduler()
    
    print("="*60)
    print("Setting up Windows Scheduled Tasks")
    print("="*60)
    
    # ------------------------------------------------------------------------
    # LINKEDIN POSTING SCHEDULES
    # ------------------------------------------------------------------------
    
    # # Daily motivational post at 9 AM every day
    # scheduler.create_task(
    #     "daily_linkedin_motivation",
    #     PROJECT_ROOT / "scheduled_tasks" / "daily_linkedin_post.py",
    #     "daily",
    #     hour=9,
    #     minute=0
    # )
    
    # # Weekly update every Monday at 10 AM
    # scheduler.create_task(
    #     "weekly_linkedin_update",
    #     PROJECT_ROOT / "scheduled_tasks" / "weekly_linkedin_post.py",
    #     "weekly",
    #     day_of_week='MON',
    #     hour=10,
    #     minute=0
    # )
    
    # # Friday wrap-up post at 5 PM
    # scheduler.create_task(
    #     "friday_wrapup",
    #     PROJECT_ROOT / "scheduled_tasks" / "friday_wrapup.py",
    #     "weekly",
    #     day_of_week='FRI',
    #     hour=17,
    #     minute=0
    # )
    
    # ------------------------------------------------------------------------
    # EMAIL REPORT SCHEDULES
    # ------------------------------------------------------------------------
    
    # # Daily email digest at 8 AM
    # scheduler.create_task(
    #     "daily_email_digest",
    #     PROJECT_ROOT / "scheduled_tasks" / "daily_email_report.py",
    #     "daily",
    #     hour=8,
    #     minute=0
    # )
    
    # # Weekly report every Friday at 5 PM
    # scheduler.create_task(
    #     "weekly_email_report",
    #     PROJECT_ROOT / "scheduled_tasks" / "weekly_email_report.py",
    #     "weekly",
    #     day_of_week='FRI',
    #     hour=17,
    #     minute=0
    # )
    
    # ------------------------------------------------------------------------
    # MAINTENANCE TASKS
    # ------------------------------------------------------------------------
    
    # # Hourly backup
    # scheduler.create_task(
    #     "hourly_backup",
    #     PROJECT_ROOT / "scheduled_tasks" / "hourly_backup.py",
    #     "hourly",
    #     interval=1
    # )
    
    # # Daily log cleanup at 2 AM
    # scheduler.create_task(
    #     "daily_log_cleanup",
    #     PROJECT_ROOT / "scheduled_tasks" / "cleanup_logs.py",
    #     "daily",
    #     hour=2,
    #     minute=0
    # )
    
    print("\n" + "="*60)
    print("Task setup complete!")
    print("Edit scheduler_windows.py to enable/disable specific tasks")
    print("="*60)
    
    # List all tasks
    scheduler.list_tasks()


# ============================================================================
# Example Scheduled Task Scripts
# ============================================================================

def create_example_task_scripts():
    """Create example task script files"""
    tasks_dir = PROJECT_ROOT / "scheduled_tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    
    # Daily LinkedIn post example
    daily_post_script = tasks_dir / "daily_linkedin_post.py"
    daily_post_script.write_text('''"""
Daily LinkedIn Motivation Post
Scheduled to run every day at 9 AM
"""
import requests
import json
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent

# Load token
token_file = PROJECT_ROOT / '.linkedin_token.json'
with open(token_file, 'r') as f:
    token_data = json.load(f)

access_token = token_data['access_token']

# Load person URN
env_file = PROJECT_ROOT / '.env'
person_urn = ""
with open(env_file, 'r') as f:
    for line in f:
        if 'LINKEDIN_PERSON_URN' in line:
            person_urn = line.split('=')[1].strip().strip('"')
            break

# Daily messages (rotates by day of week)
messages = {
    0: "Starting the week strong! 💪 What are your goals for this week? #MondayMotivation #Goals",
    1: "Tuesday tip: Consistency is key to success. Keep pushing forward! #TuesdayThoughts #Success",
    2: "Wednesday wisdom: The best time to plant a tree was 20 years ago. The second best time is now. #WednesdayWisdom",
    3: "Thursday thought: Innovation distinguishes between a leader and a follower. #ThursdayThoughts #Innovation",
    4: "Friday feeling: Celebrate your wins this week, no matter how small! 🎉 #FridayFeeling #Wins",
    5: "Saturday inspiration: Work hard on what you will become. #SaturdayMotivation #Growth",
    6: "Sunday reflection: Rest is not idle, is not indolent, is not a waste of time. #SundayVibes #Rest",
}

day_of_week = datetime.now().weekday()
message = messages.get(day_of_week, "Have a great day! #DailyPost")

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
        "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
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
    print(f"[OK] Post created: {result.get('id', '')}")
else:
    print(f"[FAIL] {response.text}")
''')
    
    print(f"[OK] Created example task script: {daily_post_script}")


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "setup":
            # Set up all scheduled tasks
            create_example_task_scripts()
            setup_common_tasks()
        
        elif command == "list":
            # List all tasks
            scheduler = WindowsTaskScheduler()
            scheduler.list_tasks()
        
        elif command == "run":
            # Run a specific task
            if len(sys.argv) > 2:
                task_name = sys.argv[2]
                scheduler = WindowsTaskScheduler()
                scheduler.run_task_now(task_name)
        
        elif command == "delete":
            # Delete a specific task
            if len(sys.argv) > 2:
                task_name = sys.argv[2]
                scheduler = WindowsTaskScheduler()
                scheduler.delete_task(task_name)
        
        elif command == "info":
            # Get info about a task
            if len(sys.argv) > 2:
                task_name = sys.argv[2]
                scheduler = WindowsTaskScheduler()
                scheduler.get_task_info(task_name)
        
        else:
            print("Usage:")
            print("  python scheduler_windows.py setup   - Set up scheduled tasks")
            print("  python scheduler_windows.py list    - List all tasks")
            print("  python scheduler_windows.py run <name> - Run a task now")
            print("  python scheduler_windows.py delete <name> - Delete a task")
            print("  python scheduler_windows.py info <name> - Get task info")
    else:
        print("Windows Task Scheduler Integration for AI Employee")
        print()
        print("Usage:")
        print("  python scheduler_windows.py setup   - Set up scheduled tasks")
        print("  python scheduler_windows.py list    - List all tasks")
        print("  python scheduler_windows.py run <name> - Run a task now")
        print("  python scheduler_windows.py delete <name> - Delete a task")
        print("  python scheduler_windows.py info <name> - Get task info")
        print()
        print("Examples:")
        print("  python scheduler_windows.py setup")
        print("  python scheduler_windows.py list")
        print("  python scheduler_windows.py run daily_linkedin_motivation")
