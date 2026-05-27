# Error States & Recovery for AI Personal Employee

## Overview
This document outlines the error handling and recovery strategies for the AI Personal Employee system. Autonomous systems will inevitably fail, and proper planning for failure modes is essential for reliability.

## 1. Error Categories and Recovery Strategies

### 1.1 Transient Errors
**Examples:** Network timeouts, API rate limits, temporary service unavailability
**Recovery Strategy:** Exponential backoff retry with jitter

**Implementation:**
- Use the `with_retry` decorator from `retry_handler.py`
- Configurable max attempts, base delay, and max delay
- Automatic exponential backoff with capped delay

### 1.2 Authentication Errors
**Examples:** Expired tokens, revoked access, credential changes
**Recovery Strategy:** Alert human operator, pause operations until resolved

**Implementation:**
- AuthenticationError exceptions trigger immediate human notification
- System pauses affected operations
- Resume only after human intervention

### 1.3 Logic Errors
**Examples:** Claude misinterpreting messages, incorrect decision making
**Recovery Strategy:** Human review queue for correction

**Implementation:**
- LogicError exceptions route to human review queue
- Tasks are held pending human approval
- System continues with other operations

### 1.4 Data Errors
**Examples:** Corrupted files, missing fields, invalid formats
**Recovery Strategy:** Quarantine problematic data, alert for review

**Implementation:**
- DataError exceptions trigger data quarantine
- Files moved to Quarantine directory with metadata
- Human notification for data review

### 1.5 System Errors
**Examples:** Orchestrator crashes, disk full, memory exhaustion
**Recovery Strategy:** Watchdog process with auto-restart

**Implementation:**
- Watchdog monitors critical processes
- Automatic restart of failed processes
- Restart limits to prevent thrashing

## 2. Retry Logic Implementation

### 2.1 Decorator Usage
The `with_retry` decorator provides configurable retry logic:

```python
from retry_handler import with_retry, TransientError

@with_retry(max_attempts=3, base_delay=1, max_delay=60)
def send_email(to, subject, body):
    # Implementation that might have transient failures
    pass
```

### 2.2 Configuration Options
- `max_attempts`: Number of retry attempts before giving up
- `base_delay`: Initial delay between retries (seconds)
- `max_delay`: Maximum delay between retries (seconds)
- `retry_exceptions`: Specific exception types to retry

## 3. Graceful Degradation

### 3.1 Component Failures
When components fail, the system degrades gracefully:

**Gmail API Down:**
- Queues outgoing emails locally in Queue directory
- Continues processing when API is restored
- Implements exponential backoff for reconnection

**Banking API Timeout:**
- Never retries payments automatically
- Always requires fresh human approval
- Holds payments in Payment_Holds queue

**Claude Code Unavailable:**
- Watchers continue collecting tasks
- Tasks queue in Claude_Queued directory
- Processes queued tasks when Claude is available

**Obsidian Vault Locked:**
- Writes to temporary folder (Temp directory)
- Syncs to vault when available
- Maintains metadata about original locations

### 3.2 Queue Processing
The system periodically processes all queues to catch up on pending work:
- Email queue processing
- Claude task queue processing
- Payment hold queue processing

## 4. Watchdog Process

### 4.1 Process Monitoring
The watchdog continuously monitors critical processes:
- Orchestrator
- Scheduler
- MCP servers (filesystem and approval)

### 4.2 Restart Logic
- Checks process status every 60 seconds (configurable)
- Restarts failed processes automatically
- Respects restart limits to prevent thrashing
- Logs all restart events
- Notifies human operators of restarts

### 4.3 Configuration
Stored in `watchdog_config.json`:
- Process commands and arguments
- Restart on failure settings
- Maximum restarts per hour
- Check interval
- Working directories for processes

## 5. Error Handling Best Practices

### 5.1 Error Classification
All errors should be classified using the ErrorCategory enum:
- Transient: Temporary issues that can be retried
- Authentication: Credential or access issues
- Logic: Incorrect decisions or interpretations
- Data: Corrupt or invalid data
- System: Infrastructure or resource issues

### 5.2 Logging
- All errors are logged with appropriate severity
- Error context and parameters are captured
- Recovery actions are logged
- Human notifications are recorded

### 5.3 Monitoring
- Health checks for all critical components
- Alerting for unrecoverable errors
- Metrics on error rates and recovery success
- Dashboard for monitoring system health

## 6. Recovery Procedures

### 6.1 Automated Recovery
Most errors are handled automatically:
- Transient errors: Retried with backoff
- Data errors: Quarantined and reported
- Process failures: Restarted by watchdog

### 6.2 Manual Recovery
Some errors require human intervention:
- Authentication errors: Credentials need renewal
- Logic errors: Decisions need human review
- System errors: Infrastructure issues need addressing

### 6.3 Recovery Verification
- After recovery, verify system state
- Check that all components are functioning
- Process any accumulated queues
- Resume normal operations gradually

## 7. Testing Error Scenarios

### 7.1 Chaos Engineering
- Inject failures to test recovery
- Test graceful degradation paths
- Verify queue processing works
- Ensure watchdog functions correctly

### 7.2 Error Injection
- Simulate network timeouts
- Mock API failures
- Test credential expiration
- Verify all error paths

## 8. Maintenance and Monitoring

### 8.1 Regular Checks
- Review error logs regularly
- Monitor queue sizes
- Check restart frequencies
- Verify backup systems

### 8.2 Performance Tuning
- Adjust retry parameters based on observed patterns
- Tune queue processing frequency
- Optimize watchdog settings
- Monitor resource usage

---
*This document should be reviewed and updated as the system evolves.*