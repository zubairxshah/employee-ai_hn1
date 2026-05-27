"""
Monday CEO Briefing Scheduler
Schedules automatic briefing generation every Monday at 8:00 AM

Uses Windows Task Scheduler
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

# Configuration
SCRIPT_PATH = Path(__file__).parent / "monday_ceo_briefing.py"
TASK_NAME = "Monday_CEO_Briefing"
TASK_TIME = "08:00"  # 8:00 AM
TASK_DAY = "MONDAY"

VAULT_PATH = r"D:\prompteng\AI_Employee_Vault"
LOGS_DIR = Path(VAULT_PATH) / "Logs"


def create_scheduled_task():
    """
    Create Windows Task Scheduler task for Monday 8 AM briefing
    """
    # Ensure logs directory exists
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    log_file = LOGS_DIR / "ceo_briefing.log"
    
    # Build the command
    python_exe = sys.executable
    script_path = str(SCRIPT_PATH.absolute())
    
    # Command to run
    command = f'{python_exe} "{script_path}" >> "{log_file}" 2>&1'
    
    # schtasks command for Monday at 8 AM
    # /D MON is the correct format (not MONDAY)
    schtasks_cmd = f'schtasks /Create /TN "{TASK_NAME}" /TR "{command}" /SC WEEKLY /D MON /ST {TASK_TIME} /RL HIGHEST /F /RU SYSTEM'
    
    print("=" * 70)
    print("  MONDAY CEO BRIEFING - SCHEDULER SETUP")
    print("=" * 70)
    print(f"\nTask Name: {TASK_NAME}")
    print(f"Schedule: Every {TASK_DAY} at {TASK_TIME}")
    print(f"Script: {script_path}")
    print(f"Log File: {log_file}")
    print("\nCreating scheduled task...")
    
    try:
        # Run schtasks command
        result = subprocess.run(
            schtasks_cmd,
            shell=True,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("\n[OK] Scheduled task created successfully!")
            print("\nTo verify:")
            print(f"  schtasks /Query /TN \"{TASK_NAME}\"")
            print("\nTo run manually:")
            print(f"  schtasks /Run /TN \"{TASK_NAME}\"")
            print("\nTo delete:")
            print(f"  schtasks /Delete /TN \"{TASK_NAME}\" /F")
            return True
        else:
            print(f"\n[ERROR] Failed to create task:")
            print(result.stderr)
            print("\nManual setup required:")
            print("1. Open Task Scheduler (taskschd.msc)")
            print("2. Create Basic Task")
            print(f"3. Name: {TASK_NAME}")
            print("4. Trigger: Weekly on Monday at 8:00 AM")
            print(f"5. Action: Start program: {python_exe}")
            print(f"   Add arguments: {script_path}")
            return False
            
    except Exception as e:
        print(f"\n[ERROR] Exception: {e}")
        return False


def remove_scheduled_task():
    """Remove the scheduled task"""
    print(f"Removing scheduled task: {TASK_NAME}")
    
    try:
        result = subprocess.run(
            f'schtasks /Delete /TN "{TASK_NAME}" /F',
            shell=True,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("[OK] Task removed successfully!")
            return True
        else:
            print(f"[ERROR] {result.stderr}")
            return False
    except Exception as e:
        print(f"[ERROR] {e}")
        return False


def check_task_exists():
    """Check if the scheduled task exists"""
    try:
        result = subprocess.run(
            f'schtasks /Query /TN "{TASK_NAME}"',
            shell=True,
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except:
        return False


def run_briefing_now():
    """Run the briefing immediately (for testing)"""
    print("=" * 70)
    print("  RUNNING CEO BRIEFING NOW (TEST)")
    print("=" * 70)
    
    try:
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH.absolute())],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent)
        )
        
        print(result.stdout)
        if result.stderr:
            print("Errors:")
            print(result.stderr)
            
        return result.returncode == 0
    except Exception as e:
        print(f"[ERROR] {e}")
        return False


def show_help():
    """Show help information"""
    print("""
Monday CEO Briefing Scheduler
=============================

Usage:
  python schedule_ceo_briefing.py [command]

Commands:
  install   - Create scheduled task (Monday 8 AM)
  remove    - Remove scheduled task
  run       - Run briefing now (test)
  status    - Check if task is scheduled
  help      - Show this help

Examples:
  python schedule_ceo_briefing.py install
  python schedule_ceo_briefing.py run
  python schedule_ceo_briefing.py status
""")


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == "install":
        create_scheduled_task()
    elif command == "remove":
        remove_scheduled_task()
    elif command == "run":
        run_briefing_now()
    elif command == "status":
        if check_task_exists():
            print(f"[OK] Task '{TASK_NAME}' is scheduled")
            print(f"       Every {TASK_DAY} at {TASK_TIME}")
        else:
            print(f"[INFO] Task '{TASK_NAME}' is NOT scheduled")
            print("       Run 'python schedule_ceo_briefing.py install' to schedule")
    elif command == "help":
        show_help()
    else:
        print(f"[ERROR] Unknown command: {command}")
        show_help()


if __name__ == "__main__":
    main()
