# AI Employee Scheduling Guide

**Last Updated:** February 22, 2026  
**Status:** ✅ Complete - Silver Tier Requirement Satisfied

---

## Overview

The AI Employee now supports **flexible task scheduling** with two complementary systems:

1. **APScheduler** - In-app scheduling (runs while the app is running)
2. **Windows Task Scheduler** - System-level scheduling (runs even when app is closed)

---

## Features

### ✅ What You Can Schedule

- **LinkedIn Posts** - Automatic posting at specific times
- **Email Reports** - Daily/weekly digests
- **Data Backups** - Regular backups of important data
- **File Monitoring** - Periodic checks for file changes
- **Custom Tasks** - Any Python function

### ✅ Scheduling Options

- **Cron-based** - Specific times (e.g., every Monday at 9 AM)
- **Interval-based** - Repeating intervals (e.g., every 30 minutes)
- **One-time** - Run once at a specific date/time
- **System events** - Run at startup, on idle, etc.

---

## Quick Start

### Option 1: In-App Scheduling (APScheduler) - RECOMMENDED

Best for: Tasks that run while your app is active

**This is the easiest option and doesn't require admin privileges.**

```bash
# Start the scheduler
python scheduler.py
```

**Edit `scheduler.py`** to enable tasks:

```python
# Uncomment tasks you want to enable

# Daily LinkedIn post at 9 AM
scheduler.add_cron_task(
    "daily_linkedin_post",
    lambda: post_to_linkedin("Good morning! #Motivation"),
    day_of_week='mon-fri',
    hour=9,
    minute=0
)

# Check emails every 15 minutes
scheduler.add_interval_task(
    "check_emails",
    lambda: print("Checking emails..."),
    minutes=15
)
```

### Option 2: Windows Task Scheduler (Requires Admin)

Best for: Tasks that run even when your app is closed

**Note:** Requires administrator privileges to create tasks.

```bash
# Run as Administrator, then execute:
python scheduler_windows.py setup
```

**Alternative:** Use the in-app scheduler (Option 1) which doesn't require admin rights.

**Edit `scheduler_windows.py`** to enable tasks:

```python
# Daily LinkedIn post at 9 AM
scheduler.create_task(
    "daily_linkedin_motivation",
    PROJECT_ROOT / "scheduled_tasks" / "daily_linkedin_post.py",
    "daily",
    hour=9,
    minute=0
)
```

---

## Usage Examples

### LinkedIn Posting

#### Example 1: Daily Motivational Post

```python
# In scheduler.py
scheduler.add_cron_task(
    "daily_motivation",
    lambda: post_to_linkedin(
        "Good morning! Ready to make today count? 💪 #MondayMotivation"
    ),
    day_of_week='mon-fri',
    hour=9,
    minute=0
)
```

#### Example 2: Weekly Update

```python
# In scheduler.py
scheduler.add_cron_task(
    "weekly_update",
    lambda: post_to_linkedin(
        "Weekly update: Exciting progress on our AI projects! #WeeklyUpdate"
    ),
    day_of_week='mon',
    hour=10,
    minute=0
)
```

#### Example 3: Windows Task Scheduler

```bash
# Create a daily task
python scheduler_windows.py setup
```

This creates tasks in Windows Task Scheduler that run even when your app is closed.

### Email Reports

#### Daily Digest

```python
scheduler.add_cron_task(
    "daily_digest",
    lambda: send_email_report(
        "recipient@example.com",
        "Daily Digest - AI Employee",
        "Here's your daily summary..."
    ),
    hour=8,
    minute=0
)
```

#### Weekly Report

```python
scheduler.add_cron_task(
    "weekly_report",
    lambda: send_email_report(
        "recipient@example.com",
        "Weekly Report - AI Employee",
        "Weekly summary and metrics..."
    ),
    day_of_week='fri',
    hour=17,
    minute=0
)
```

---

## Management Commands

### Windows Task Scheduler

```bash
# List all scheduled tasks
python scheduler_windows.py list

# Run a task immediately (for testing)
python scheduler_windows.py run daily_linkedin_motivation

# Get task details
python scheduler_windows.py info daily_linkedin_motivation

# Delete a task
python scheduler_windows.py delete daily_linkedin_motivation
```

### View Tasks in Windows

1. Press `Win + R`
2. Type: `taskschd.msc`
3. Press Enter
4. Look for tasks starting with `AI_Employee_`

---

## Scheduling Patterns

### Common Patterns

| Pattern | Code | Description |
|---------|------|-------------|
| Every day at 9 AM | `hour=9, minute=0` | Daily morning task |
| Every weekday at 9 AM | `day_of_week='mon-fri', hour=9` | Business hours only |
| Every Monday at 10 AM | `day_of_week='mon', hour=10` | Weekly meeting reminder |
| Every 15 minutes | `minutes=15` | Frequent checks |
| Every hour | `hours=1` | Hourly tasks |
| First of month | `day=1, hour=0` | Monthly reports |

### Cron Expression Examples

```python
# Every minute (for testing)
scheduler.add_cron_task("test", my_func, minute='*')

# Every 15 minutes
scheduler.add_cron_task("quarterly_check", my_func, minute='*/15')

# Every day at 6 PM
scheduler.add_cron_task("evening_post", my_func, hour=18, minute=0)

# Every weekday at 9 AM
scheduler.add_cron_task("morning_post", my_func, 
                       day_of_week='mon-fri', hour=9, minute=0)

# Every Monday and Thursday at 2 PM
scheduler.add_cron_task("bi_weekly", my_func,
                       day_of_week='mon,thu', hour=14, minute=0)
```

---

## Task Execution Log

All scheduled task executions are logged to:

```
D:\prompteng\AI_Employee_Vault\Scheduled_Tasks\execution_log.json
```

View execution history:

```python
from scheduler import TaskScheduler

scheduler = TaskScheduler()

# Get all executions
history = scheduler.get_execution_history(limit=20)

# Get executions for specific task
task_history = scheduler.get_execution_history("daily_linkedin_post", limit=10)

for entry in task_history:
    print(f"{entry['timestamp']}: {'OK' if entry['success'] else 'FAIL'}")
```

---

## Best Practices

### ✅ Do's

- **Test tasks manually first** - Ensure the function works before scheduling
- **Use descriptive names** - `daily_linkedin_motivation` not `task1`
- **Log execution results** - Track successes and failures
- **Handle errors gracefully** - Don't let one failure crash the scheduler
- **Start with intervals** - Test with frequent intervals, then reduce frequency
- **Use Windows Scheduler for critical tasks** - More reliable than in-app

### ❌ Don'ts

- **Don't schedule too frequently** - Respect API rate limits
- **Don't schedule during maintenance windows** - Avoid conflicts
- **Don't forget to monitor** - Check execution logs regularly
- **Don't create conflicting tasks** - Avoid duplicate posts

---

## Troubleshooting

### Task Not Running

**In-App Scheduler:**
- Make sure `scheduler.py` is running
- Check for Python errors in console
- Verify task is listed: `scheduler.list_tasks()`

**Windows Task Scheduler:**
- Open Task Scheduler (`taskschd.msc`)
- Find your task (`AI_Employee_*`)
- Check "Last Run Result" - should be `0x0`
- Right-click → "Run" to test manually

### Task Runs But Fails

1. **Check execution log:**
   ```
   D:\prompteng\AI_Employee_Vault\Scheduled_Tasks\execution_log.json
   ```

2. **Common issues:**
   - Token expired → Re-authenticate
   - API rate limit → Reduce frequency
   - Network error → Check connectivity

### Windows Task Scheduler Issues

**Task runs but window flashes:**
- Normal behavior for background tasks
- Check execution log for results

**Task doesn't run:**
- Check task is "Enabled"
- Verify trigger settings
- Check "Conditions" tab (power/network settings)

---

## API Reference

### TaskScheduler Class

```python
from scheduler import TaskScheduler

scheduler = TaskScheduler()

# Add cron-based task
scheduler.add_cron_task(
    "task_name",
    function_to_call,
    hour=9,
    minute=0,
    day_of_week='mon-fri'
)

# Add interval-based task
scheduler.add_interval_task(
    "task_name",
    function_to_call,
    minutes=30
)

# Add one-time task
from datetime import datetime, timedelta
tomorrow = datetime.now() + timedelta(days=1)
scheduler.add_onetime_task(
    "one_time_task",
    function_to_call,
    run_date=tomorrow
)

# Start scheduler
scheduler.start()

# List tasks
scheduler.list_tasks()

# Stop scheduler
scheduler.shutdown()
```

### WindowsTaskScheduler Class

```python
from scheduler_windows import WindowsTaskScheduler

scheduler = WindowsTaskScheduler()

# Create daily task
scheduler.create_task(
    "daily_post",
    script_path,
    "daily",
    hour=9,
    minute=0
)

# Create weekly task
scheduler.create_task(
    "weekly_update",
    script_path,
    "weekly",
    day_of_week='MON',
    hour=10,
    minute=0
)

# List all tasks
scheduler.list_tasks()

# Run task now (for testing)
scheduler.run_task_now("daily_post")

# Delete task
scheduler.delete_task("daily_post")
```

---

## Files Reference

| File | Purpose |
|------|---------|
| `scheduler.py` | In-app scheduler with APScheduler |
| `scheduler_windows.py` | Windows Task Scheduler integration |
| `scheduled_tasks/` | Directory for scheduled task scripts |
| `Vault/Scheduled_Tasks/execution_log.json` | Task execution history |

---

## Silver Tier Status

✅ **Basic Scheduling** - **COMPLETE**

This satisfies the final Silver Tier requirement:

| Requirement | Status |
|-------------|--------|
| All Bronze requirements | ✅ Complete |
| Two or more Watcher scripts | ✅ Complete |
| Automatically Post on LinkedIn | ✅ Complete |
| Claude reasoning loop (Plan.md) | ✅ Complete |
| One working MCP for external action | ✅ Complete |
| Human-in-the-loop approval | ✅ Complete |
| **Basic scheduling** | ✅ **COMPLETE** |
| All AI as Agent Skills | ✅ Complete |

**Silver Tier: 100% Complete! 🎉**

---

## Next Steps

Now that scheduling is complete, you can:

1. **Enable specific tasks** - Edit scheduler files and uncomment tasks
2. **Create custom tasks** - Add your own scheduled functions
3. **Monitor execution** - Check logs regularly
4. **Move to Gold Tier** - Add advanced features like:
   - Image attachments for posts
   - Analytics retrieval
   - Company page posting
   - Advanced workflow automation

---

**Ready to schedule!** 🚀
