"""
Test different LinkedIn URN formats for posting
"""
import requests
import json

# Load token from file
with open('.linkedin_token.json', 'r') as f:
    token_data = json.load(f)

ACCESS_TOKEN = token_data['access_token']
PERSON_URN = token_data['person_urn']  # urn:li:person:-bj_2BokKd

print(f"Person URN from token: {PERSON_URN}")

# Extract just the ID
person_id = PERSON_URN.split(':')[-1]
print(f"Person ID: {person_id}")

# Test different URN formats
urn_formats = [
    f"urn:li:person:{person_id}",
    f"urn:li:member:{person_id}",
    f"urn:li:organization:{person_id}",
    person_id,  # Just the ID
]

API_BASE = "https://api.linkedin.com/v2"
headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "X-Restli-Protocol-Version": "2.0.0",
    "Content-Type": "application/json"
}

print("\n" + "="*70)
print("Testing URN Formats for Posting")
print("="*70)

for author_urn in urn_formats:
    print(f"\n[*] Testing: {author_urn}")
    
    post_data = {
        "author": author_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {
                    "text": f"Test post with URN format: {author_urn}"
                },
                "shareMediaCategory": "NONE"
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }
    
    response = requests.post(
        f"{API_BASE}/ugcPosts",
        headers=headers,
        json=post_data,
        timeout=30
    )
    
    print(f"    Status: {response.status_code}")
    
    if response.status_code == 201:
        result = response.json()
        print(f"    [OK] SUCCESS!")
        print(f"    Post ID: {result.get('id', 'N/A')}")
        print(f"    Post URL: https://www.linkedin.com/feed/update/{result.get('id', '').replace(':', '_')}")
        break
    else:
        print(f"    [FAIL] {response.text[:200]}")

print("\n" + "="*70)
