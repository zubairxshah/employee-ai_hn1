"""
Post to LinkedIn with proper formatting
Usage: python post_to_linkedin.py "Your message here"
"""
import requests
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent

# Load token
token_file = PROJECT_ROOT / '.linkedin_token.json'
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

# Get message from command line or use default
if len(sys.argv) > 1:
    message = sys.argv[1]
else:
    # Default milestone message with proper newlines
    message = """🚀 Exciting Milestone Achieved!

I'm thrilled to share that we've successfully reached Silver Tier completion with the CodeWorks AI Employee MCP server.

This achievement marks a major step forward — we now have seamless integration with both Gmail and LinkedIn, enabling automated messaging and streamlined workflows.

Silver Tier isn't just a badge; it represents the dedication to building robust, transparent, and scalable systems that empower smarter collaboration.

Onward to the next tier and even greater possibilities! 🌟

#AI #Automation #LinkedInAPI #MilestonesAchieved #TechInnovation #ArtificialIntelligence #WorkflowAutomation #SilverTier #CodeWorks #DigitalTransformation"""

print("Posting message to LinkedIn...")
print("-" * 60)

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
