"""
WhatsApp Setup Test Script
Tests WhatsApp notification functionality
"""

import os
import sys
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_whatsapp():
    """Test WhatsApp notification"""
    print("=" * 60)
    print("WhatsApp Test Notification")
    print("=" * 60)
    
    # Load phone number from .env
    from pathlib import Path
    env_file = Path(__file__).parent / '.env'
    phone_number = None
    
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                if line.startswith('WHATSAPP_NOTIFICATION_PHONE='):
                    phone_number = line.split('=', 1)[1].strip().strip('"').strip("'")
                    break
    
    if not phone_number:
        print("\n[ERROR] Phone number not configured in .env")
        print("\nAdd this line to .env:")
        print("  WHATSAPP_NOTIFICATION_PHONE=+12125551234")
        print("\nReplace +12125551234 with your actual phone number.")
        return False
    
    # Mask phone number for display (show last 4 digits)
    masked = phone_number[:-4] + "****" if len(phone_number) > 4 else "***"
    
    print(f"\nSending test message to: {masked}")
    print("\n⚠️  IMPORTANT:")
    print("   A browser window will open with WhatsApp Web QR code.")
    print("   Scan the QR code with your phone:")
    print("   1. Open WhatsApp on phone")
    print("   2. Tap Menu (⋮) or Settings")
    print("   3. Select 'Linked Devices'")
    print("   4. Tap 'Link a Device'")
    print("   5. Point camera at QR code")
    print("\n⏳  This may take 30-60 seconds...")
    print("\nPress Enter to continue or Ctrl+C to cancel...")
    input()
    
    try:
        import pywhatkit
        
        # Test message
        message = f"""🔔 WhatsApp Test Notification

This is a test message from your AI Employee system.

If you receive this, WhatsApp notifications are working correctly!

Time: {time.strftime('%Y-%m-%d %H:%M')}
"""
        
        print("\n[OK] Starting WhatsApp Web...")
        print("[INFO] Browser will open shortly...")
        
        # Send message (opens in browser)
        # wait_time: seconds to wait for WhatsApp Web to load
        # tab_close: close browser after sending
        # close_time: seconds to wait before closing tab
        pywhatkit.sendwhatmsg_instantly(
            phone_no=phone_number,
            message=message,
            wait_time=20,  # Wait 20 seconds for WhatsApp Web to load
            tab_close=True,
            close_time=5
        )
        
        print("\n[OK] Message sent successfully!")
        print(f"     Check your WhatsApp: {masked}")
        print("\n✅ WhatsApp is configured correctly!")
        return True
        
    except ImportError:
        print("\n[ERROR] pywhatkit not installed!")
        print("\nInstall with:")
        print("  pip install pywhatkit")
        return False
        
    except Exception as e:
        error_msg = str(e)
        print(f"\n[ERROR] Failed to send message: {error_msg}")
        
        if "Could not load" in error_msg or "browser" in error_msg.lower():
            print("\n💡 Browser Issue Detected")
            print("   Try these steps:")
            print("   1. Close all browser windows")
            print("   2. Make sure Chrome/Chromium is installed")
            print("   3. Run the script again")
            print("   4. Or install pywhatkit: pip install pywhatkit --upgrade")
        elif "phone number" in error_msg.lower() or "number" in error_msg.lower():
            print("\n💡 Phone Number Issue Detected")
            print("   Check your phone number format in .env:")
            print("   - Must include country code (e.g., +1, +44, +91)")
            print("   - No spaces, dashes, or parentheses")
            print("   - Example: +12125551234")
        elif "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
            print("\n💡 Timeout Issue Detected")
            print("   WhatsApp Web took too long to load.")
            print("   Try again and scan QR code quickly.")
            print("   Or check your internet connection.")
        
        return False


def check_prerequisites():
    """Check if prerequisites are met"""
    print("=" * 60)
    print("WhatsApp Setup - Prerequisites Check")
    print("=" * 60)
    
    all_ok = True
    
    # Check pywhatkit
    print("\n[1/3] Checking pywhatkit installation...")
    try:
        import pywhatkit
        print("      [OK] pywhatkit is installed")
    except ImportError:
        print("      [FAIL] pywhatkit is NOT installed")
        print("             Run: pip install pywhatkit")
        all_ok = False
    
    # Check .env file
    print("\n[2/3] Checking .env configuration...")
    from pathlib import Path
    env_file = Path(__file__).parent / '.env'
    
    if env_file.exists():
        print("      [OK] .env file exists")
        
        # Check phone number
        phone_configured = False
        with open(env_file, 'r') as f:
            for line in f:
                if line.startswith('WHATSAPP_NOTIFICATION_PHONE='):
                    phone_configured = True
                    phone_number = line.split('=', 1)[1].strip().strip('"').strip("'")
                    if phone_number and phone_number.startswith('+'):
                        masked = phone_number[:-4] + "****" if len(phone_number) > 4 else "***"
                        print(f"      [OK] Phone number configured: {masked}")
                    else:
                        print(f"      [WARN] Phone number format may be incorrect: {phone_number}")
                        print(f"             Should start with + (e.g., +12125551234)")
                    break
        
        if not phone_configured:
            print("      [WARN] Phone number NOT configured")
            print("             Add: WHATSAPP_NOTIFICATION_PHONE=+12125551234")
    else:
        print("      [FAIL] .env file NOT found")
        all_ok = False
    
    # Check WhatsApp MCP server
    print("\n[3/3] Checking WhatsApp MCP server...")
    try:
        import requests
        response = requests.get('http://localhost:8004/capabilities', timeout=3)
        if response.status_code == 200:
            print("      [OK] WhatsApp MCP is running on port 8004")
        else:
            print("      [WARN] WhatsApp MCP responded with unexpected status")
    except:
        print("      [INFO] WhatsApp MCP is NOT running")
        print("             Start with: python mcp_servers\\whatsapp_mcp.py")
    
    print("\n" + "=" * 60)
    
    if all_ok:
        print("✅ All prerequisites met! Ready to test.")
        return True
    else:
        print("⚠️  Some prerequisites missing. Please fix them first.")
        return False


def main():
    """Main function"""
    print("\n" + "=" * 60)
    print("   WhatsApp Notification Setup")
    print("=" * 60)
    print("\nThis will test WhatsApp notifications for your AI Employee.")
    print("\nSteps:")
    print("  1. Check prerequisites")
    print("  2. Send test message")
    print("  3. Verify receipt")
    print("\n" + "=" * 60)
    
    # Check prerequisites
    if not check_prerequisites():
        print("\n⚠️  Please fix the issues above before testing.")
        print("\nQuick setup:")
        print("  1. Install pywhatkit: pip install pywhatkit")
        print("  2. Edit .env and add: WHATSAPP_NOTIFICATION_PHONE=+12125551234")
        print("  3. Run this script again")
        return
    
    # Run test
    print("\n" + "=" * 60)
    success = test_whatsapp()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ WhatsApp setup complete!")
        print("\nNext steps:")
        print("  1. Start workflow executor: python approval_workflow_executor.py")
        print("  2. Create an approval request")
        print("  3. You'll receive WhatsApp notification automatically")
    else:
        print("❌ WhatsApp test failed!")
        print("\nTroubleshooting:")
        print("  - See WHATSAPP_SETUP_GUIDE.md for detailed help")
        print("  - Check that pywhatkit is installed: pip show pywhatkit")
        print("  - Verify phone number format in .env")
    print("=" * 60)


if __name__ == '__main__':
    main()
