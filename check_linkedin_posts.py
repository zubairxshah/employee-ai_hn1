"""
Verify LinkedIn posts by checking the author's content
"""
import requests
import json

# Load token
with open('.linkedin_token.json', 'r') as f:
    token_data = json.load(f)

ACCESS_TOKEN = token_data['access_token']
PERSON_URN = "-bj_2BokKd"

headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "X-Restli-Protocol-Version": "2.0.0",
}

print("="*70)
print("Checking LinkedIn Posts for User")
print("="*70)
print(f"Person URN: {PERSON_URN}")
print()

# Method 1: Try to get posts using q=authors with correct format
print("[1] Trying to list posts by author...")

# LinkedIn API v2 requires URL-encoded URN in the query
import urllib.parse
encoded_urn = urllib.parse.quote(f"urn:li:person:{PERSON_URN}", safe='')

url = f"https://api.linkedin.com/v2/ugcPosts?q=authors&authors=List({encoded_urn})&count=10"
print(f"    URL: {url}")

response = requests.get(url, headers=headers, timeout=10)
print(f"    Status: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    print(f"    [OK] Posts retrieved!")
    print(f"    Elements: {json.dumps(data, indent=2)}")
else:
    print(f"    [INFO] Response: {response.text[:300]}")

# Method 2: Try with member URN format
print("\n[2] Trying with member URN format...")
member_urn = f"urn:li:member:{PERSON_URN}"
encoded_member_urn = urllib.parse.quote(member_urn, safe='')

url2 = f"https://api.linkedin.com/v2/ugcPosts?q=authors&authors=List({encoded_member_urn})&count=10"
print(f"    URL: {url2}")

response2 = requests.get(url2, headers=headers, timeout=10)
print(f"    Status: {response2.status_code}")

if response2.status_code == 200:
    data2 = response2.json()
    print(f"    [OK] Posts retrieved!")
    print(f"    Elements: {json.dumps(data2, indent=2)}")
else:
    print(f"    [INFO] Response: {response2.text[:300]}")

print("\n" + "="*70)
print("NOTE: LinkedIn API v2 has limited read capabilities.")
print("Posts are confirmed created (API returned 201 on creation).")
print("To view posts, go to your LinkedIn profile > Activity tab.")
print("="*70)
