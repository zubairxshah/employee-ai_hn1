"""
Test /me endpoint with fresh token to get Member ID
"""
import requests
import json

# Fresh token from .linkedin_token.json
ACCESS_TOKEN = "AQX8JVI01hVsXQwgVc59hLuQInGZBwUkJD7VamerlWGBzNnFSS-9l2LrWRysdke-8mSjYGPJPE94QeREOc32iQ_gbrCbtkOixzqf0zcETPLkzYzBcNf-l5uQCcGj01W6WDvn_VJdWdJgV0OW01K8O4U6B6TgYQGgE7oJKJKgFhzSVu28AqngpQNHIkG3rOom0vl-2MFvl2ciAQGJToUQc52Xx19dPlquDQPiHjsnK6pE-KzjXR4qMyWB23law68xYZzHRgDx93P8E8Bt9A9aqRPAlmi0WxZLW6B6ETWtep9GlkX3vaF3nIra841nc61F1AMATV90YY_-RfPpl_y4n0gvJjv36g"

API_BASE = "https://api.linkedin.com/v2"

headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "X-Restli-Protocol-Version": "2.0.0",
    "LinkedIn-Version": "202402"
}

print("="*70)
print("Testing /me Endpoint with Fresh Token")
print("="*70)

# Test different endpoints
endpoints = [
    ("/me", "Basic /me"),
    ("/me?projection=(id)", "ID only"),
    ("/me?projection=(id,firstName,lastName)", "With name"),
    ("/me?projection=(id,localizedFirstName)", "With localized name"),
]

member_id = None

for endpoint, desc in endpoints:
    print(f"\n[*] Testing: {desc}")
    print(f"    URL: {API_BASE}{endpoint}")
    
    response = requests.get(f"{API_BASE}{endpoint}", headers=headers, timeout=10)
    
    print(f"    Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"    [OK] Response: {json.dumps(data, indent=2)}")
        
        if 'id' in data and data['id']:
            member_id = data['id']
            print(f"    [OK] MEMBER ID: {member_id}")
            break
    else:
        print(f"    [FAIL] {response.text[:300]}")

print("\n" + "="*70)
print("RESULT")
print("="*70)

if member_id:
    print(f"[OK] MEMBER ID FOUND: {member_id}")
    print(f"\nUpdate your .env file:")
    print(f"    LINKEDIN_PERSON_URN={member_id}")
    print(f"\nUpdate .linkedin_token.json:")
    token_json = {
        "access_token": ACCESS_TOKEN,
        "expires_at": "2026-04-23T00:07:42",
        "person_urn": member_id,
        "updated": "2026-02-22T00:07:43"
    }
    print(f"    {json.dumps(token_json, indent=2)}")
else:
    print("[FAIL] Could not retrieve Member ID from /me endpoint")
    print("\nReason: The 'w_member_social' scope only allows posting,")
    print("        not profile access. You need to add OpenID Connect")
    print("        product to your LinkedIn app.")
    print("\nALTERNATIVE - Find Member ID manually:")
    print("1. Go to https://www.linkedin.com/in/your-profile")
    print("2. Right-click -> View Page Source (Ctrl+U)")
    print("3. Search for: memberId or urn:li:member")
    print("4. Copy the numeric ID (8-10 digits)")
    print("5. Add to .env: LINKEDIN_PERSON_URN=<numeric_id>")
