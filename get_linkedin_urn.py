"""
Get LinkedIn Person URN - Automated approach
Opens LinkedIn and helps extract your Person URN
"""

import webbrowser
import time

print("="*60)
print("Get Your LinkedIn Person URN")
print("="*60)
print()
print("Opening LinkedIn in your browser...")
print()

# Open LinkedIn profile
webbrowser.open("https://www.linkedin.com/in/me")

print("STEP 1: Get your profile URL")
print("-"*60)
print("1. Your profile should have opened")
print("2. Copy your profile URL from the address bar")
print("   Example: https://www.linkedin.com/in/john-doe-123456789/")
print()

input("Press Enter after copying your profile URL...")

print()
print("STEP 2: Find your Person URN")
print("-"*60)
print("Open this URL in a new tab:")
print()
print("https://www.linkedin.com/developers/tools/ugc/posts/create")
print()
print("This tool will show your Person URN at the top of the page.")
print("It will look like: urn:li:person:ABC123456")
print()

webbrowser.open("https://www.linkedin.com/developers/tools/ugc/posts/create")

print("STEP 3: Add URN to .env file")
print("-"*60)
print("Once you have your Person URN:")
print("1. Open: D:\\prompteng\\employee\\.env")
print("2. Find the line: LINKEDIN_PERSON_URN=")
print("3. Add just the ID number (not the urn:li:person: prefix)")
print()
print("Example:")
print("  If your URN is: urn:li:person:ABC123456")
print("  Add: LINKEDIN_PERSON_URN=ABC123456")
print()
print("4. Save the file")
print("5. Restart MCP servers: python start_mcp_servers.py")
print()
print("="*60)
