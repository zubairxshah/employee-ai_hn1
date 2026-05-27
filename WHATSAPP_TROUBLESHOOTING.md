# WhatsApp Troubleshooting Guide

**Issue:** Browser opens but closes immediately, workflow executor shuts down

**Date:** February 22, 2026

---

## 🐛 Problem

When you try to send WhatsApp notifications:
1. Browser opens for a few seconds
2. Shows WhatsApp Web briefly
3. Browser closes automatically
4. Workflow executor may crash

---

## ✅ Fixes Applied

### 1. Fixed Phone Number Format
Removed quotes from `.env`:
```bash
# Before (WRONG):
WHATSAPP_NOTIFICATION_PHONE="+10000000000"

# After (CORRECT):
WHATSAPP_NOTIFICATION_PHONE=+10000000000
```

### 2. Increased Wait Times
Changed pywhatkit parameters:
```python
# Before:
wait_time=15, tab_close=True

# After:
wait_time=30, tab_close=False  # Keep browser open
```

### 3. Better Error Handling
Workflow executor now catches WhatsApp errors and continues:
```python
# WhatsApp errors are non-fatal
# Email workflow continues even if WhatsApp fails
```

### 4. Debug Test Script
Created `test_whatsapp_debug.py` with:
- Detailed error messages
- Longer wait times
- Browser stays open for verification

---

## 🔧 How to Test

### Step 1: Run Debug Test

```bash
cd /d "D:\prompteng\employee"
python test_whatsapp_debug.py
```

**What will happen:**
1. Phone number displayed: `+10000000000`
2. Confirms format is correct (starts with `+`)
3. Waits 5 seconds before opening browser
4. Opens Chrome with WhatsApp Web
5. **QR code appears - scan within 30 seconds:**
   - Open WhatsApp on phone
   - Menu → Linked Devices → Link a Device
   - Point camera at QR code
6. After scanning, message sends
7. Browser **stays open** for 60 seconds
8. You can verify message was sent
9. Browser closes automatically

### Step 2: Check Results

**SUCCESS:**
- You received test message on WhatsApp
- Browser showed "Message sent"
- Console shows "SUCCESS! WhatsApp is working!"

**FAILURE - See troubleshooting below**

---

## ⚠️ Common Issues & Solutions

### Issue 1: Browser Closes Immediately

**Symptom:** Browser opens then closes in 1-2 seconds

**Cause:** pywhatkit default behavior or error

**Solution:**
```bash
# Use the debug test instead
python test_whatsapp_debug.py
```

This keeps browser open with `tab_close=False`.

---

### Issue 2: QR Code Expires

**Symptom:** QR code shows "Expired" before you can scan

**Solution:**
1. Refresh browser (F5)
2. New QR code appears
3. Scan immediately:
   - Have WhatsApp ready on phone
   - Menu → Linked Devices → Link a Device
   - Scan within 10 seconds

**Tip:** Open WhatsApp on phone BEFORE browser opens.

---

### Issue 3: Workflow Executor Crashes

**Symptom:** Executor stops after WhatsApp attempt

**Cause:** Unhandled exception from pywhatkit

**Solution:** Already fixed in `approval_workflow_executor.py`:
```python
# Now catches all WhatsApp errors
except requests.exceptions.Timeout:
    print("[INFO] WhatsApp notification timed out - continuing anyway")
    return True, {"message": "Notification timeout - check browser"}
```

**To restart executor:**
```bash
python approval_workflow_executor.py
```

---

### Issue 4: "Could not load browser"

**Symptom:** Error mentions browser or ChromeDriver

**Solutions:**

**Option A: Install Chrome**
```
Download from: https://www.google.com/chrome/
```

**Option B: Use existing Chrome**
```bash
# Make sure Chrome is in PATH
# Or set CHROME_BIN environment variable
set CHROME_BIN=C:\Program Files\Google\Chrome\Application\chrome.exe
```

**Option C: Skip WhatsApp, use email only**
```bash
# WhatsApp is optional
# Email workflow works without it
```

---

### Issue 5: Phone Number Format Error

**Symptom:** Error mentions phone number or "invalid format"

**Check your `.env`:**
```bash
# CORRECT:
WHATSAPP_NOTIFICATION_PHONE=+10000000000

# WRONG (quotes):
WHATSAPP_NOTIFICATION_PHONE="+10000000000"

# WRONG (spaces):
WHATSAPP_NOTIFICATION_PHONE=+92 311 2014288

# WRONG (no +):
WHATSAPP_NOTIFICATION_PHONE=923112014288
```

**Pakistan numbers:**
- Start with `+92`
- Remove leading `0` from mobile code
- Example: `0311 2014288` → `+10000000000`

---

### Issue 6: Message Not Received

**Symptom:** No error but no message on WhatsApp

**Check:**

1. **Browser window** - Do you see WhatsApp Web?
2. **Chat opened** - Is your number's chat visible?
3. **Message typed** - Is message in the input box?
4. **Send clicked** - Did pywhatkit click send?

**Common causes:**
- QR code not scanned
- Wrong phone number
- Internet connection issue
- WhatsApp Web not fully loaded

**Solution:**
```bash
# Run debug test and watch the browser
python test_whatsapp_debug.py

# Keep browser open - don't close it
# Watch what happens step by step
```

---

## 🎯 Quick Diagnostic

### Run This Command
```bash
python test_whatsapp_debug.py
```

### Expected Output
```
======================================================================
   WhatsApp Test - Detailed Debug Mode
======================================================================

Phone number: +10000000000
Length: 13 characters
Starts with +: True

======================================================================
This test will:
  1. Open browser with WhatsApp Web
  2. Display QR code (scan with your phone)
  3. Wait 30 seconds for you to scan
  4. Send test message
  5. Keep browser open so you can see result

WARNING: DO NOT close the browser - it will close automatically after 60 seconds
======================================================================

Press Enter to start or Ctrl+C to cancel...
[Enter pressed]

[STEP 1] Opening WhatsApp Web...
[STEP 2] Sending message via pywhatkit...
[Browser opens with QR code]
[You scan QR code]
[STEP 3] Message sent!
         Check your WhatsApp phone for the test message.

======================================================================
Browser is kept open for debugging.
You should see WhatsApp Web with the message sent.
======================================================================

SUCCESS! WhatsApp is working!
```

### If You See This
✅ **Phone number correct** → Format is good  
✅ **Browser opens** → Chrome working  
✅ **QR code appears** → WhatsApp Web loading  
⏳ **Waiting for scan** → Scan with phone now!  
✅ **Message sent** → Success!  
✅ **Browser stays open** → Can verify  

### If You See Errors
❌ **Phone number wrong** → Check `.env` file  
❌ **Browser doesn't open** → Install Chrome  
❌ **QR code doesn't appear** → Refresh browser (F5)  
❌ **Error message** → Read error and see troubleshooting above  

---

## 📝 Manual Test (If Scripts Don't Work)

### Test pywhatkit Directly

```python
import pywhatkit

# Test message
pywhatkit.sendwhatmsg_instantly(
    phone_no="+10000000000",
    message="Test from Python",
    wait_time=30,
    tab_close=False
)
```

Run this in Python directly to see exact errors.

---

## 🔐 Privacy Note

Your phone number `+10000000000` is stored in `.env` file:
- ✅ Never commit to git
- ✅ Only used for WhatsApp Web
- ✅ Not sent to any servers
- ✅ Local automation only

---

## ✅ Alternative: Email-Only Workflow

If WhatsApp continues to have issues, you can skip it entirely:

**WhatsApp is OPTIONAL** - the approval workflow works fine with email only:

1. Approval request created → File in `Pending_Approval/`
2. You review in Obsidian
3. Move to `Approved/`
4. Email sent automatically
5. File moved to `Done/`

**No WhatsApp needed!**

---

## 📞 Support Commands

### Check Configuration
```bash
# View phone number from .env
python -c "from pathlib import Path; print([l for l in Path('.env').read_text().split('\n') if 'WHATSAPP_NOTIFICATION_PHONE' in l])"
```

### Test WhatsApp
```bash
python test_whatsapp_debug.py
```

### Start Workflow (with WhatsApp)
```bash
python approval_workflow_executor.py
```

### Start Workflow (Email Only - WhatsApp MCP not running)
```bash
# Just don't start whatsapp_mcp.py
# Executor will skip WhatsApp and do email only
python approval_workflow_executor.py
```

---

**Status:** Fixes applied, ready to test  
**Next Step:** Run `python test_whatsapp_debug.py`
