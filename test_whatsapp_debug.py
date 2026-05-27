"""
Improved WhatsApp Test - Keeps browser open and shows detailed errors
"""

import os
import sys
import time
from pathlib import Path

# Get phone number from .env
def get_phone_number():
    env_file = Path(__file__).parent / '.env'
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                if line.startswith('WHATSAPP_NOTIFICATION_PHONE='):
                    return line.split('=', 1)[1].strip().strip('"').strip("'")
    return None

print("=" * 70)
print("   WhatsApp Test - Detailed Debug Mode")
print("=" * 70)

phone = get_phone_number()
if not phone:
    print("\n[ERROR] Phone number not found in .env")
    exit(1)

print(f"\nPhone number: {phone}")
print(f"Length: {len(phone)} characters")
print(f"Starts with +: {phone.startswith('+')}")

if not phone.startswith('+'):
    print("\n[WARN] Phone number should start with + (e.g., +10000000000)")
    print("       Please fix in .env file")

print("\n" + "=" * 70)
print("This test will:")
print("  1. Open browser with WhatsApp Web")
print("  2. Display QR code (scan with your phone)")
print("  3. Wait 30 seconds for you to scan")
print("  4. Send test message")
print("  5. Keep browser open so you can see result")
print("\nWARNING: DO NOT close the browser - it will close automatically after 60 seconds")
print("=" * 70)
print("\nStarting in 3 seconds... (or press Ctrl+C to cancel)")
time.sleep(3)

try:
    import pywhatkit
    
    # Test message
    message = f"""🔔 WhatsApp Test Notification

This is a test from your AI Employee system.

Phone: {phone}
Time: {time.strftime('%Y-%m-%d %H:%M:%S')}

If you see this message, WhatsApp notifications are working!
"""
    
    print("\n[STEP 1] Opening WhatsApp Web...")
    print("         Please wait - browser will open in 5 seconds...")
    time.sleep(5)
    
    print("\n[STEP 2] Sending message via pywhatkit...")
    print("         Browser should open with WhatsApp Web...")
    
    # Use sendwhatmsg_instantly with longer wait times
    # Parameters:
    # - phone_no: phone number with country code
    # - message: message to send
    # - wait_time: time to wait for WhatsApp Web to load (seconds)
    # - tab_close: whether to close tab after sending (False = keep open)
    # - close_time: time to wait before closing (if tab_close=True)
    
    pywhatkit.sendwhatmsg_instantly(
        phone_no=phone,
        message=message,
        wait_time=30,      # Wait 30 seconds for WhatsApp Web to load
        tab_close=False,   # DON'T close tab - keep it open
        close_time=5
    )
    
    print("\n[STEP 3] Message sent!")
    print("         Check your WhatsApp phone for the test message.")
    print("\n" + "=" * 70)
    print("Browser is kept open for debugging.")
    print("You should see WhatsApp Web with the message sent.")
    print("=" * 70)
    print("\nSUCCESS! WhatsApp is working!")
    print("\nThe browser will close in 60 seconds...")
    print("Or press Ctrl+C to exit now.")
    
    # Wait 60 seconds before closing
    for i in range(60, 0, -1):
        time.sleep(1)
        if i % 10 == 0:
            print(f"   Closing in {i} seconds...")
    
    print("\nBrowser should close now.")
    
except ImportError as e:
    print(f"\n[ERROR] pywhatkit not installed: {e}")
    print("\nInstall with:")
    print("  pip install pywhatkit")
    
except Exception as e:
    error_msg = str(e)
    print(f"\n[ERROR] Failed: {error_msg}")
    print("\n" + "=" * 70)
    print("Troubleshooting:")
    print("=" * 70)
    
    if "Could not load" in error_msg or "browser" in error_msg.lower():
        print("\n🌐 BROWSER ISSUE:")
        print("   - Make sure Google Chrome is installed")
        print("   - Try running as Administrator")
        print("   - Close all Chrome windows and try again")
        print("   - Install ChromeDriver: pip install webdriver-manager")
        
    elif "phone" in error_msg.lower() or "number" in error_msg.lower():
        print("\n📱 PHONE NUMBER ISSUE:")
        print(f"   - Your number: {phone}")
        print("   - Must start with + (e.g., +10000000000)")
        print("   - No spaces, dashes, or parentheses")
        print("   - Check .env file: WHATSAPP_NOTIFICATION_PHONE=+10000000000")
        
    elif "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
        print("\n⏱️  TIMEOUT ISSUE:")
        print("   - Internet connection may be slow")
        print("   - WhatsApp Web took too long to load")
        print("   - Try again and scan QR code faster")
        print("   - Check your internet connection")
        
    elif "QR" in error_msg or "qr" in error_msg or "scan" in error_msg.lower():
        print("\n📷 QR CODE ISSUE:")
        print("   - QR code expires after ~30 seconds")
        print("   - Refresh browser (F5) to get new QR code")
        print("   - Scan quickly with WhatsApp on your phone:")
        print("     WhatsApp → Menu → Linked Devices → Link a Device")
        
    else:
        print("\n❓ UNKNOWN ERROR:")
        print(f"   Error details: {error_msg}")
        print("   Check WHATSAPP_SETUP_GUIDE.md for help")
    
    print("\n" + "=" * 70)
    print("Press Enter to exit...")
    input()
