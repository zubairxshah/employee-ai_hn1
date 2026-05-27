"""
Verify LinkedIn posts exist by fetching post details
"""
import requests
import json

# Load token
with open('.linkedin_token.json', 'r') as f:
    token_data = json.load(f)

ACCESS_TOKEN = token_data['access_token']

# Post IDs from our test posts
post_ids = [
    "urn:li:share:7431057431364943872",
    "urn:li:share:7431057638026584064",
    "urn:li:share:7431058596576120832",  # Latest
]

headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "X-Restli-Protocol-Version": "2.0.0",
}

print("="*70)
print("Verifying LinkedIn Posts")
print("="*70)

for post_id in post_ids:
    print(f"\n[*] Checking: {post_id}")
    
    # Try to fetch the post
    url = f"https://api.linkedin.com/v2/ugcPosts/{post_id}"
    response = requests.get(url, headers=headers, timeout=10)
    
    print(f"    Status: {response.status_code}")
    
    if response.status_code == 200:
        post_data = response.json()
        print(f"    [OK] Post exists!")
        
        # Extract some info
        lifecycle_state = post_data.get('lifecycleState', 'UNKNOWN')
        print(f"    State: {lifecycle_state}")
        
        visibility = post_data.get('visibility', {})
        vis_type = list(visibility.values())[0] if visibility else 'UNKNOWN'
        print(f"    Visibility: {vis_type}")
        
    else:
        print(f"    [FAIL] {response.text[:200]}")

print("\n" + "="*70)

# Also check what posts we have access to
print("\n[*] Listing your recent posts...")
search_url = "https://api.linkedin.com/v2/ugcPosts?q=authors&authors=List(urn:li:person:-bj_2BokKd)&count=5"
response = requests.get(search_url, headers=headers, timeout=10)

print(f"    List posts status: {response.status_code}")
if response.status_code == 200:
    posts = response.json()
    print(f"    Posts found: {json.dumps(posts, indent=2)[:500]}")
else:
    print(f"    Response: {response.text[:300]}")
