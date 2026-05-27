"""
Fetch LinkedIn Member ID using existing access token
"""
import requests

# Your existing valid access token
ACCESS_TOKEN = "AQSzB0Q0YWBXNGqMlimtIWSAi4pn98oms8AN02UmFOe9D_IEPj3m-TCP-PGzwizj7uyP1a94GjCm9K_qpD21Ivh_Y75gnfUVIZCgfs_TAmyzVtz_VJQhSjMcV9bbp--2QCfm4qXvUhbTancv6wyXoAfhPVTxfqzCveO_tp8dDzOYAJdCQGc4Ruu0t5e2kDaAMJxc3Cx38_z2uHCpoxA"

# Try different LinkedIn API endpoints to get member ID
endpoints = [
    ("v2/me", "Standard me endpoint"),
    ("v2/me?projection=(id,firstName,lastName,profilePicture)", "me with projection"),
    ("v2/me?projection=(id)", "me with id only"),
]

headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "X-Restli-Protocol-Version": "2.0.0",
    "LinkedIn-Version": "202402"
}

print("Testing LinkedIn API endpoints to find Member ID...\n")
print("=" * 60)

for endpoint, description in endpoints:
    print(f"\n[*] Testing: {description}")
    print(f"    Endpoint: {endpoint}")
    
    try:
        response = requests.get(
            f"https://api.linkedin.com/{endpoint}",
            headers=headers,
            timeout=10
        )
        
        print(f"    Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"    [OK] SUCCESS!")
            print(f"    Response: {data}")
            
            # Extract ID
            member_id = data.get('id', '')
            if member_id:
                print(f"\n[OK] YOUR MEMBER ID: {member_id}")
                print(f"    Add to .env: LINKEDIN_PERSON_URN={member_id}")
                break
        else:
            print(f"    [FAIL] Failed: {response.text[:200]}")
            
    except Exception as e:
        print(f"    [FAIL] Error: {e}")

print("\n" + "=" * 60)
