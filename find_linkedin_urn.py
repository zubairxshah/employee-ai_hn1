"""
LinkedIn Person URN Finder
Helps you find your LinkedIn Person URN for API integration
"""

import requests
import webbrowser

def find_urn_from_profile():
    """
    Guide user to find their Person URN manually
    """
    print("="*60)
    print("LinkedIn Person URN Finder")
    print("="*60)
    print()
    print("Your LinkedIn Person URN is needed for posting via the API.")
    print()
    print("METHOD 1: From your LinkedIn profile URL")
    print("-"*60)
    print("1. Go to your LinkedIn profile")
    print("2. Copy your profile URL, e.g.:")
    print("   https://www.linkedin.com/in/your-name-123456789/")
    print("3. The number at the end is NOT your URN, but helps identify you")
    print()
    
    open_profile = input("Open your LinkedIn profile now? (y/n): ").strip().lower()
    if open_profile == 'y':
        webbrowser.open("https://www.linkedin.com/in/me")
        print("Profile opened. Copy the URL and note the identifier.")
    
    print()
    print("METHOD 2: Use LinkedIn API Explorer (Recommended)")
    print("-"*60)
    print("1. Go to: https://www.linkedin.com/developers/tools/ugc/posts/create")
    print("2. This will show your URN in the format: urn:li:person:XXXXXXXX")
    print()
    
    open_explorer = input("Open LinkedIn API explorer? (y/n): ").strip().lower()
    if open_explorer == 'y':
        webbrowser.open("https://www.linkedin.com/developers/tools/ugc/posts/create")
    
    print()
    print("METHOD 3: Use this curl command (if you have r_liteprofile scope)")
    print("-"*60)
    print("curl -H \"Authorization: Bearer YOUR_ACCESS_TOKEN\" \\")
    print("     https://api.linkedin.com/v2/me")
    print()
    
    print("="*60)
    print("Once you have your Person URN (format: urn:li:person:XXXXXXXX):")
    print("="*60)
    print("1. Open your .env file")
    print("2. Add or update this line:")
    print("   LINKEDIN_PERSON_URN=XXXXXXXX")
    print("   (just the ID number, not the full urn:li:person: prefix)")
    print("3. Restart the MCP servers:")
    print("   python start_mcp_servers.py")
    print()
    
    person_urn = input("Enter your Person URN ID (or press Enter to skip): ").strip()
    
    if person_urn:
        # Remove common prefixes
        if person_urn.startswith("urn:li:person:"):
            person_urn = person_urn.replace("urn:li:person:", "")
        
        # Update .env file
        env_file = "D:\\prompteng\\employee\\.env"
        try:
            with open(env_file, 'r') as f:
                content = f.read()
            
            # Update or add LINKEDIN_PERSON_URN
            if "LINKEDIN_PERSON_URN=" in content:
                import re
                content = re.sub(
                    r'LINKEDIN_PERSON_URN=.*',
                    f'LINKEDIN_PERSON_URN={person_urn}',
                    content
                )
            else:
                content += f"\nLINKEDIN_PERSON_URN={person_urn}\n"
            
            with open(env_file, 'w') as f:
                f.write(content)
            
            print(f"\n[OK] Updated .env file with LINKEDIN_PERSON_URN={person_urn}")
            print("\nNow restart the MCP servers:")
            print("  python start_mcp_servers.py")
            
        except Exception as e:
            print(f"\n[ERROR] Could not update .env file: {e}")
            print(f"Please manually add this line to .env:")
            print(f"  LINKEDIN_PERSON_URN={person_urn}")
    else:
        print("\nNo URN entered. You can add it later to the .env file.")


if __name__ == '__main__':
    try:
        find_urn_from_profile()
    except KeyboardInterrupt:
        print("\n\nInterrupted.")
    except Exception as e:
        print(f"\nError: {e}")
