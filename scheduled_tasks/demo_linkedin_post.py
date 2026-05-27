"""
Demo Scheduled Task - Test LinkedIn Posting
This is a simple test task for scheduling
"""
import requests
import json
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent

print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting scheduled LinkedIn post...")

# Load token
token_file = PROJECT_ROOT / '.linkedin_token.json'
if not token_file.exists():
    print("[FAIL] Token file not found")
    exit(1)

with open(token_file, 'r') as f:
    token_data = json.load(f)

access_token = token_data['access_token']

# Load person URN
env_file = PROJECT_ROOT / '.env'
person_urn = ""
with open(env_file, 'r') as f:
    for line in f:
        if 'LINKEDIN_PERSON_URN' in line:
            person_urn = line.split('=')[1].strip().strip('"')
            break

if not person_urn:
    print("[FAIL] Person URN not configured")
    exit(1)

# Create test post with properly formatted date
now = datetime.now()
formatted_date = now.strftime("%B %d, %Y")
formatted_time = now.strftime("%I:%M %p")

message = f"🤖 Automated post from AI Employee Scheduler!\n\nThis post was automatically scheduled and published at {formatted_time} on {formatted_date}.\n\n#Automation #AI #ScheduledPost"

headers = {
    "Authorization": f"Bearer {access_token}",
    "X-Restli-Protocol-Version": "2.0.0",
    "Content-Type": "application/json"
}

post_data = {
    "author": f"urn:li:person:{person_urn}",
    "lifecycleState": "PUBLISHED",
    "specificContent": {
        "com.linkedin.ugc.ShareContent": {
            "shareCommentary": {"text": message},
            "shareMediaCategory": "NONE"
        }
    },
    "visibility": {
        "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
    }
}

print("[*] Posting to LinkedIn...")

response = requests.post(
    "https://api.linkedin.com/v2/ugcPosts",
    headers=headers,
    json=post_data,
    timeout=30
)

if response.status_code == 201:
    result = response.json()
    post_id = result.get('id', '')
    post_url = f"https://www.linkedin.com/feed/update/{post_id.replace(':', '_')}"
    print(f"[OK] Post created successfully!")
    print(f"Post ID: {post_id}")
    print(f"URL: {post_url}")
else:
    print(f"[FAIL] {response.status_code}")
    print(f"Response: {response.text}")
