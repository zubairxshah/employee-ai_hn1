"""
Direct WhatsApp Test - Test pywhatkit directly
"""

import pywhatkit
import time

# Configuration
PHONE = "+10000000000"  # From .env

print("=" * 70)
print("   DIRECT WHATSAPP TEST")
print("=" * 70)

message = f"""🔔 AI Employee - Direct WhatsApp Test

This is a DIRECT test from your AI Employee system.

If you receive this message, it means:
1. Pywhatkit is working
2. Phone number is correct
3. WhatsApp Web authentication successful

Test sent at: {time.strftime('%Y-%m-%d %H:%M:%S')}

Best regards,
AI Employee System
"""

print(f"\nSending to: {PHONE}")
print("\nWARNING: Browser will open in 5 seconds...")
print("    WhatsApp Web QR code will appear")
print("    Scan with your phone if prompted")
print("\nStarting...")
time.sleep(5)

try:
    print("\n[STEP 1] Opening WhatsApp Web...")
    print("[INFO] Please wait - browser loading...")
    
    # Send message
    pywhatkit.sendwhatmsg_instantly(
        phone_no=PHONE,
        message=message,
        wait_time=20,
        tab_close=True,
        close_time=3
    )
    
    print("\n[OK] Message sent successfully!")
    print("\n" + "=" * 70)
    print("   WHATSAPP MESSAGE SENT!")
    print("=" * 70)
    print(f"""
Details:
  To: {PHONE}
  Message: Test message from AI Employee
  
Check your WhatsApp now!
If you don't see it:
  - Wait 1-2 minutes for delivery
  - Check if WhatsApp Web was scanned
  - Check internet connection
""")
    print("=" * 70)
    
except Exception as e:
    error_msg = str(e)
    print(f"\n[ERROR] Failed to send WhatsApp message: {error_msg}")
    
    if "Could not load" in error_msg or "browser" in error_msg.lower():
        print("\n💡 Browser Issue:")
        print("   - Make sure Google Chrome is installed")
        print("   - Try running as Administrator")
        
    elif "phone" in error_msg.lower() or "number" in error_msg.lower():
        print("\n💡 Phone Number Issue:")
        print(f"   - Check number format: {PHONE}")
        print("   - Must start with + (e.g., +10000000000)")
        
    elif "timeout" in error_msg.lower():
        print("\n💡 Timeout Issue:")
        print("   - WhatsApp Web took too long to load")
        print("   - Check internet connection")
        print("   - Try again")
        
    elif "QR" in error_msg or "qr" in error_msg or "scan" in error_msg.lower():
        print("\n💡 QR Code Issue:")
        print("   - Scan QR code with WhatsApp on your phone")
        print("   - WhatsApp → Menu → Linked Devices → Link a Device")
