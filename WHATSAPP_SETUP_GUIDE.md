# WhatsApp Notification Setup Guide

**Status:** Setup Required  
**Date:** February 22, 2026

---

## 📋 Overview

This guide will help you set up WhatsApp notifications for approval requests. When someone creates an approval request, you'll receive a WhatsApp message instantly.

---

## ⚙️ Prerequisites

- Windows 10/11
- Python 3.10+
- WhatsApp Web account (free)
- A phone that can receive WhatsApp messages

---

## 🔧 Setup Steps

### Step 1: Install pywhatkit Dependency

**Option A: Install Now (Recommended)**

```bash
cd /d "D:\prompteng\employee"
pip install pywhatkit
```

**Note:** Installation may take 5-10 minutes as it installs browser automation dependencies.

**Option B: Skip WhatsApp (Use Email Only)**

WhatsApp notifications are **optional**. The approval workflow works fine with email only. You can skip this setup and add it later.

---

### Step 2: Configure Your Phone Number

Edit `.env` file and add your WhatsApp phone number:

```bash
# Open .env in notepad
notepad .env
```

Add this line (replace with your actual phone number):

```bash
# WhatsApp Notification Phone (for approval alerts)
# Format: +1234567890 (with country code, no spaces, no + sign issues)
# Examples:
#   US: +12125551234
#   UK: +442071234567
#   IN: +919876543210
WHATSAPP_NOTIFICATION_PHONE=+12125551234
```

**Important:** 
- Include country code (e.g., +1 for US, +44 for UK, +91 for India)
- No spaces, dashes, or parentheses
- Must start with `+`

**Examples:**
| Country | Format | Example |
|---------|--------|---------|
| USA | `+1` + area code + number | `+12125551234` |
| UK | `+44` + number (no leading 0) | `+442071234567` |
| India | `+91` + 10 digit number | `+919876543210` |
| Canada | `+1` + area code + number | `+14165551234` |

---

### Step 3: Test WhatsApp MCP Server

**Start WhatsApp MCP Server:**

```bash
cd /d "D:\prompteng\employee"
python mcp_servers\whatsapp_mcp.py
```

**Expected Output:**
```
WhatsApp MCP Server starting...
Default notification phone: +12125551234
Note: WhatsApp Web must be logged in for notifications to work
* Running on http://localhost:8004
```

**Keep this terminal open** - the server needs to stay running.

---

### Step 4: Test WhatsApp Notification

**Open a new terminal** and run the test:

```bash
cd /d "D:\prompteng\employee"
python test_whatsapp_setup.py
```

**What Will Happen:**

1. A browser window will open (Chrome/Chromium)
2. WhatsApp Web QR code will appear
3. **Scan the QR code with your phone:**
   - Open WhatsApp on phone
   - Tap Menu (⋮) or Settings
   - Select "Linked Devices"
   - Tap "Link a Device"
   - Point camera at QR code
4. After scanning, the message will be sent
5. Browser will close automatically

**Expected Output:**
```
============================================================
WhatsApp Test Notification
============================================================
Sending test message to: +12125551234

[OK] Browser opened - WhatsApp Web loading...
[OK] QR code displayed - Please scan with your phone...
[OK] WhatsApp Web authenticated
[OK] Message sent successfully!
Check your WhatsApp for the test message.
```

---

### Step 5: Start Everything Together

**For Full Workflow (Email + WhatsApp):**

```bash
# Terminal 1 - Start all MCP servers (includes WhatsApp on port 8004)
python start_mcp_servers.py

# Terminal 2 - Start workflow executor (sends WhatsApp + emails)
python approval_workflow_executor.py
```

**Expected Output from Executor:**
```
============================================================
Approval Workflow Executor Starting...
============================================================
Monitoring: D:\prompteng\AI_Employee_Vault\Approved (for execution)
Monitoring: D:\prompteng\AI_Employee_Vault\Pending_Approval (for notifications)
Email MCP: http://localhost:8001
WhatsApp MCP: http://localhost:8004
Poll interval: 5 seconds
Press Ctrl+C to stop
============================================================
```

---

## 🧪 Testing the Complete Workflow

### Test 1: Create Approval Request

Move or create a file in `Pending_Approval`:

```markdown
---
type: approval_request
action: send_email
amount: $250.00
recipient: client@example.com
reason: Test invoice
---

## Request Details
- Action: send_email
- Amount: $250.00
```

### Expected Flow

1. **WhatsApp Notification** (within 5-10 seconds):
   ```
   🔔 Approval Required
   
   Action: send_email
   Amount: $250.00
   Recipient: client@example.com
   
   Please review in Obsidian vault.
   ```

2. **You Review in Obsidian:**
   - Open `Pending_Approval/APPROVAL_*.md`
   - Review details
   - Move to `Approved/` folder

3. **Email Sent** (within 5-10 seconds):
   - Executor detects approval
   - Sends email via Gmail
   - Moves file to `Done/`

---

## ⚠️ Troubleshooting

### Issue 1: pywhatkit Installation Fails

**Symptom:** `pip install pywhatkit` fails or hangs

**Solution:**
```bash
# Try upgrading pip first
python -m pip install --upgrade pip

# Then install pywhatkit
pip install pywhatkit

# If still fails, install dependencies manually
pip install Pillow pyautogui requests wikipedia Flask
```

---

### Issue 2: QR Code Doesn't Appear

**Symptom:** Browser opens but no QR code

**Solutions:**

1. **Wait longer** - WhatsApp Web may take 10-30 seconds to load
2. **Refresh the page** - Press F5 in the browser
3. **Check internet connection** - WhatsApp Web requires internet
4. **Try incognito mode** - Clear browser cache

---

### Issue 3: QR Code Expires

**Symptom:** QR code shows "Expired" message

**Solution:**
- Refresh the page (F5)
- A new QR code will appear
- Scan quickly - codes expire after ~30 seconds

---

### Issue 4: Message Not Sent After Scanning

**Symptom:** QR code scanned but no message sent

**Possible Causes:**

1. **Wrong phone number format**
   - Ensure format: `+12125551234` (with +, no spaces)
   - Edit `.env` and fix `WHATSAPP_NOTIFICATION_PHONE`

2. **WhatsApp Web not fully loaded**
   - Wait for chats to appear in left sidebar
   - Then try again

3. **Browser closed too quickly**
   - Increase `wait_time` in code (default: 15 seconds)

---

### Issue 5: Receiving Messages on Wrong Number

**Symptom:** Message sent to different number

**Solution:**
- Double-check phone number in `.env`
- Format: `+` + country code + number (no spaces)
- Example: `+12125551234` NOT `12125551234` or `+1 212-555-1234`

---

### Issue 6: WhatsApp MCP Won't Start

**Symptom:** Port 8004 error or immediate crash

**Solutions:**

1. **Check if port 8004 is already in use:**
   ```bash
   netstat -ano | findstr :8004
   ```
   If in use, kill the process or use different port.

2. **Check pywhatkit is installed:**
   ```bash
   pip show pywhatkit
   ```
   If not found, install: `pip install pywhatkit`

---

## 🔐 Privacy & Security

### What Data Is Shared

- **Phone number** - Stored locally in `.env` (never committed to git)
- **Message content** - Approval details (action, amount, recipient)
- **No message history** - Only new notifications

### Security Best Practices

1. **Keep `.env` private** - Never commit to version control
2. **Use dedicated number** - Consider using a business number
3. **Review notifications** - Messages contain sensitive financial data
4. **Secure your phone** - Use phone lock screen + WhatsApp lock

---

## 📊 How It Works

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│              WHATSAPP NOTIFICATION FLOW                  │
└─────────────────────────────────────────────────────────┘

1. Claude creates approval request
   ↓
   File: Pending_Approval/APPROVAL_*.md
   ↓
2. Workflow Executor detects (polls every 5s)
   ↓
3. Calls WhatsApp MCP (port 8004)
   ↓
4. WhatsApp MCP uses pywhatkit
   ↓
5. Opens browser → WhatsApp Web
   ↓
6. Sends message to your phone
   ↓
7. Browser closes automatically
   ↓
8. You receive notification!
```

### Message Format

```
🔔 Approval Required

Action: send_email
Amount: $1,500.00
Recipient: client@example.com
Reason: January 2026 invoice

Please review in Obsidian vault.

Time: 2026-02-22 15:30
```

---

## 🚀 Quick Commands Reference

### Install Dependencies
```bash
pip install pywhatkit
```

### Start WhatsApp MCP
```bash
python mcp_servers\whatsapp_mcp.py
```

### Test WhatsApp
```bash
python test_whatsapp_setup.py
```

### Start Full System
```bash
# Terminal 1
python start_mcp_servers.py

# Terminal 2
python approval_workflow_executor.py
```

### Check Configuration
```bash
# View phone number (last 4 digits only)
python -c "from pathlib import Path; env=Path('.env').read_text(); print([l for l in env.split('\n') if 'WHATSAPP' in l and 'PHONE' in l])"
```

---

## 📝 Alternative: Email-Only Workflow

If WhatsApp setup is too complex, you can use **email-only** notifications:

### Option 1: Email Notifications to Yourself

Modify approval workflow to send you an email instead of WhatsApp:

```python
# Instead of WhatsApp, send email notification
email_data = {
    "to": "your_email@gmail.com",
    "subject": "🔔 Approval Required",
    "body": "New approval request created..."
}
```

### Option 2: SMS via Email

Many carriers offer email-to-SMS:

| Carrier | Email Format | Example |
|---------|-------------|---------|
| Verizon | number@vtext.com | 12125551234@vtext.com |
| AT&T | number@txt.att.net | 12125551234@txt.att.net |
| T-Mobile | number@tmomail.net | 12125551234@tmomail.net |

Set `WHATSAPP_NOTIFICATION_PHONE` to your SMS email address.

---

## ✅ Setup Checklist

- [ ] pywhatkit installed (`pip install pywhatkit`)
- [ ] Phone number configured in `.env`
- [ ] WhatsApp MCP server starts without errors
- [ ] Test message received on WhatsApp
- [ ] Workflow executor running
- [ ] Full workflow tested (approval → WhatsApp → approve → email)

---

## 📞 Support

If you encounter issues:

1. Check logs: `Vault\Logs\whatsapp_notifications.log`
2. Review error messages in terminal
3. Ensure WhatsApp Web is accessible: https://web.whatsapp.com
4. Try manual test: `python test_whatsapp_setup.py`

---

**Status:** Ready for setup  
**Estimated Time:** 10-15 minutes  
**Difficulty:** Medium

---

## 🎯 Next Steps

1. **Install pywhatkit** (10 minutes)
2. **Add phone number to .env** (1 minute)
3. **Test with test_whatsapp_setup.py** (3 minutes)
4. **Start full workflow** (1 minute)

**Ready to proceed?** Run:
```bash
pip install pywhatkit
```
