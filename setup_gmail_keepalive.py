"""
Register the Gmail OAuth keepalive with Windows Task Scheduler

Google revokes unused refresh tokens and deletes unused OAuth clients after
6 months. A weekly ping keeps both clocks from ever running out, and Windows
Task Scheduler is used rather than scheduler.py because it survives reboots
and needs no long-running process -- the failure this guards against is
precisely nothing running for months.

Usage:
    python setup_gmail_keepalive.py            # create/update the task
    python setup_gmail_keepalive.py --delete   # remove it

Verify or run on demand:
    python scheduler_windows.py run gmail_keepalive
    schtasks /Query /TN AI_Employee_gmail_keepalive /V /FO LIST
"""

import subprocess
import sys
from pathlib import Path

from scheduler_windows import WindowsTaskScheduler, TASK_NAME_PREFIX

PROJECT_ROOT = Path(__file__).parent.absolute()
TASK_NAME = "gmail_keepalive"
FULL_TASK_NAME = f"{TASK_NAME_PREFIX}{TASK_NAME}"
SCRIPT_PATH = PROJECT_ROOT / "scheduled_tasks" / "gmail_keepalive.py"

# Weekly is ample against a 6-month deadline, and leaves room for the machine
# to be off for weeks at a time without the margin getting thin.
SCHEDULE = {"day_of_week": "MON", "hour": 9, "minute": 0}


def enable_start_when_available():
    """
    Ask Task Scheduler to run a missed task once the machine is back up.

    schtasks does not expose this, and without it a keepalive on a desktop
    that happens to be off every Monday at 9 would never fire at all.
    """
    ps = (
        f"$t = Get-ScheduledTask -TaskName '{FULL_TASK_NAME}'; "
        f"$t.Settings.StartWhenAvailable = $true; "
        f"Set-ScheduledTask -TaskName '{FULL_TASK_NAME}' -Settings $t.Settings | Out-Null"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
        capture_output=True, text=True
    )
    return result.returncode == 0, result.stderr.strip()


def main():
    scheduler = WindowsTaskScheduler()

    if "--delete" in sys.argv:
        return 0 if scheduler.delete_task(TASK_NAME) else 1

    if not SCRIPT_PATH.exists():
        print(f"[FAIL] Keepalive script not found: {SCRIPT_PATH}")
        return 1

    print("=" * 60)
    print("  Gmail Keepalive - Scheduled Task Setup")
    print("=" * 60)
    print(f"\nScript:   {SCRIPT_PATH}")
    print(f"Schedule: Weekly, {SCHEDULE['day_of_week']} "
          f"{SCHEDULE['hour']:02d}:{SCHEDULE['minute']:02d}\n")

    # LIMITED, not HIGHEST: the keepalive needs no admin rights, and requesting
    # them would make this setup fail outside an elevated terminal.
    created = scheduler.create_task(
        TASK_NAME, SCRIPT_PATH, "weekly", run_level="LIMITED", **SCHEDULE
    )
    if not created:
        print("\n[FAIL] Could not create the task. See the schtasks error above.")
        return 1

    ok, err = enable_start_when_available()
    if ok:
        print("[OK] Missed runs will execute when the machine next starts")
    else:
        print(f"[WARN] Could not set StartWhenAvailable: {err}")
        print("       The task still runs on schedule, but a run missed while")
        print("       the machine is off will be skipped rather than caught up.")

    print("\n" + "=" * 60)
    print("Done. Verify with:")
    print(f"  schtasks /Query /TN {FULL_TASK_NAME} /V /FO LIST")
    print(f"  python scheduler_windows.py run {TASK_NAME}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
