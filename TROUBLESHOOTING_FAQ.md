# Troubleshooting FAQ for AI Personal Employee

## Overview
This document provides solutions to common issues encountered when setting up and running the AI Personal Employee system.

## Setup Issues

### Q: Claude Code says "command not found"
**A:** Ensure Claude Code is installed globally and your PATH is configured. Run: 
```bash
npm install -g @anthropic/claude-code
```
Then restart your terminal.

### Q: Obsidian vault isn't being read by Claude
**A:** Check that you're running Claude Code from the vault directory, or using the --cwd flag to point to it. Verify file permissions allow read access.

### Q: Gmail API returns 403 Forbidden
**A:** Your OAuth consent screen may need verification, or you haven't enabled the Gmail API in Google Cloud Console. Check the project settings.

### Q: Playwright fails to install for WhatsApp watcher
**A:** Run the following command to install Playwright browsers:
```bash
playwright install chromium
```

### Q: MCP servers won't start
**A:** Ensure Flask is installed and check that the server ports aren't already in use. Verify that all dependencies are installed.

## Runtime Issues

### Q: Watcher scripts stop running overnight
**A:** Use a process manager like PM2 (Node.js) or supervisord (Python) to keep them alive. Alternatively, implement the Watchdog pattern from Section 7.

### Q: Claude is making incorrect decisions
**A:** Review your Company_Handbook.md rules. Add more specific examples. Consider lowering autonomy thresholds so more actions require approval.

### Q: MCP server won't connect
**A:** Check that the server process is running (`ps aux | grep mcp`). Verify the path in mcp.json is absolute. Check Claude Code logs for connection errors.

### Q: Files aren't being moved between directories
**A:** Verify that the file system watcher has proper permissions to read and write to the vault directories. Check that the directories exist.

### Q: CEO Briefing isn't generated automatically
**A:** Verify that the scheduler is running and that the cron/schedule configuration is correct. Check the scheduler logs for errors.

## Security Concerns

### Q: How do I know my credentials are safe?
**A:** Never commit .env files. Use environment variables. Regularly rotate credentials. Implement the audit logging from Section 6 to track all access.

### Q: What if Claude tries to pay the wrong person?
**A:** That's why HITL is critical for payments. Any payment action should create an approval file first. Never auto-approve payments to new recipients.

### Q: My audit logs show suspicious activity
**A:** Immediately disable the affected MCP server and review all recent actions. Change relevant credentials and investigate the source of the issue.

## Performance Issues

### Q: System is running slowly
**A:** Check that you don't have too many watchers running simultaneously. Consider staggering their check intervals. Monitor system resources.

### Q: Claude is taking too long to respond
**A:** Verify your internet connection. Consider optimizing prompts to be more specific. Check if the Claude API is experiencing high latency.

### Q: Disk space is filling up quickly
**A:** Regularly clean up old log files and archived data. Check that the system isn't creating duplicate files unexpectedly.

## Integration Issues

### Q: Gmail watcher isn't detecting new emails
**A:** Verify that the Gmail API credentials are correct and have the necessary scopes. Check that the email filters are properly configured.

### Q: WhatsApp watcher isn't working
**A:** Ensure WhatsApp Web is properly authenticated and the session is still valid. Check that the keywords list is properly configured.

### Q: Bank transaction integration isn't working
**A:** Verify that your banking API credentials are correct and the API is accessible. Check that the transaction format matches what the system expects.

## Error Recovery

### Q: How do I recover from a system crash?
**A:** The watchdog process should automatically restart critical services. Check the queue directories for any pending tasks that need manual processing.

### Q: Files got stuck in quarantine
**A:** Review the quarantined files and their metadata to understand why they were flagged. After verifying they're safe, manually move them to the appropriate directory.

### Q: Payment got stuck in approval queue
**A:** Check the approval queue in the vault and verify the payment details. If legitimate, move the file to the approved directory to complete the transaction.

## Best Practices

### Regular Maintenance
- Daily: 2-minute dashboard check
- Weekly: 15-minute action log review
- Monthly: 1-hour comprehensive audit
- Quarterly: Full security and access review

### Monitoring
- Set up alerts for critical system failures
- Regularly review audit logs for anomalies
- Monitor system resource usage
- Keep dependencies updated

### Security
- Regularly rotate all API keys and credentials
- Review access logs regularly
- Ensure sensitive data stays local
- Keep the system updated with security patches

## Getting Help

If you encounter an issue not covered in this FAQ:
1. Check the system logs in the vault's Logs directory
2. Verify all configuration files are properly set up
3. Ensure all required services are running
4. Review the documentation for the specific component causing issues
5. If the issue persists, consider temporarily reducing automation levels while investigating