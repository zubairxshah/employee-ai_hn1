"""
Quick Setup - Enable Demo Scheduled Task
Run this to set up a demo scheduled task
"""
from scheduler_windows import WindowsTaskScheduler, create_example_task_scripts
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.absolute()

print("="*60)
print("AI Employee - Quick Task Setup")
print("="*60)

# Create example task scripts (skip, already created)
print("[OK] Example task scripts already created")

# Create scheduler
scheduler = WindowsTaskScheduler()

# Create a demo task that runs at 1 PM daily (for testing)
print("\nCreating demo scheduled task...")
scheduler.create_task(
    "demo_daily_post",
    PROJECT_ROOT / "scheduled_tasks" / "demo_linkedin_post.py",
    "daily",
    hour=13,
    minute=0
)

print("\n" + "="*60)
print("Setup Complete!")
print("="*60)
print("\nDemo task created:")
print("  - Name: AI_Employee_demo_daily_post")
print("  - Schedule: Daily at 1:00 PM")
print("  - Script: scheduled_tasks/demo_linkedin_post.py")
print("\nTo view in Windows Task Scheduler:")
print("  1. Press Win + R")
print("  2. Type: taskschd.msc")
print("  3. Press Enter")
print("  4. Look for: AI_Employee_demo_daily_post")
print("\nTo test the task now:")
print("  python scheduler_windows.py run demo_daily_post")
print("\nTo delete the task:")
print("  python scheduler_windows.py delete demo_daily_post")
print("="*60)

# List all tasks
scheduler.list_tasks()
