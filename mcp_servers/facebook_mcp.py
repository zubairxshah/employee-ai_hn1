"""
Facebook/Instagram MCP Server
Provides Facebook Page and Instagram posting via Graph API v19.0

Port: 8006
"""

import os
import sys
import json
import requests
from pathlib import Path
from flask import Flask, request, jsonify, redirect
from datetime import datetime, timedelta
from urllib.parse import quote, urlencode

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from security_config import get_security_config
from secure_action_executor import get_secure_executor


app = Flask(__name__)

VAULT_PATH = os.getenv("VAULT_PATH", r"D:\prompteng\AI_Employee_Vault")
SECURITY_CONFIG = get_security_config()
SECURE_EXECUTOR = get_secure_executor()

# Facebook/Instagram API configuration
GRAPH_API_BASE = "https://graph.facebook.com/v19.0"
FACEBOOK_AUTH_URL = "https://www.facebook.com/v19.0/dialog/oauth"
FACEBOOK_TOKEN_URL = f"{GRAPH_API_BASE}/oauth/access_token"

# Facebook configuration
FACEBOOK_CONFIG = {
    "app_id": "",
    "app_secret": "",
    "redirect_uri": "http://localhost:8006/callback",
    "access_token": "",         # Short-lived user token
    "page_access_token": "",    # Long-lived page token
    "page_id": "",
    "instagram_account_id": "",
    "expires_at": None,
}


def load_facebook_config():
    """Load Facebook configuration from environment or config file"""
    global FACEBOOK_CONFIG

    # Try loading from .env file
    env_file = Path(__file__).parent.parent / '.env'
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    value = value.strip().strip('"').strip("'")
                    if key == 'FACEBOOK_APP_ID':
                        FACEBOOK_CONFIG['app_id'] = value
                    elif key == 'FACEBOOK_APP_SECRET':
                        FACEBOOK_CONFIG['app_secret'] = value
                    elif key == 'FACEBOOK_REDIRECT_URI':
                        FACEBOOK_CONFIG['redirect_uri'] = value
                    elif key == 'FACEBOOK_PAGE_ID':
                        FACEBOOK_CONFIG['page_id'] = value
                    elif key == 'FACEBOOK_PAGE_ACCESS_TOKEN':
                        FACEBOOK_CONFIG['page_access_token'] = value
                    elif key == 'INSTAGRAM_ACCOUNT_ID':
                        FACEBOOK_CONFIG['instagram_account_id'] = value

    # Check for token file
    token_file = Path(__file__).parent.parent / '.facebook_token.json'
    if token_file.exists():
        try:
            with open(token_file, 'r') as f:
                token_data = json.load(f)
                FACEBOOK_CONFIG['access_token'] = token_data.get('access_token', '')
                FACEBOOK_CONFIG['page_access_token'] = token_data.get('page_access_token', '')
                FACEBOOK_CONFIG['page_id'] = token_data.get('page_id', '') or FACEBOOK_CONFIG['page_id']
                FACEBOOK_CONFIG['instagram_account_id'] = token_data.get('instagram_account_id', '') or FACEBOOK_CONFIG['instagram_account_id']
                FACEBOOK_CONFIG['expires_at'] = token_data.get('expires_at')
        except Exception:
            pass

    return FACEBOOK_CONFIG


def save_facebook_token(access_token, page_access_token="", page_id="",
                        instagram_account_id="", expires_in=5184000):
    """Save Facebook tokens to file"""
    token_file = Path(__file__).parent.parent / '.facebook_token.json'

    token_data = {
        "access_token": access_token,
        "page_access_token": page_access_token,
        "page_id": page_id,
        "instagram_account_id": instagram_account_id,
        "expires_at": (datetime.now() + timedelta(seconds=expires_in)).isoformat(),
        "updated": datetime.now().isoformat()
    }

    with open(token_file, 'w') as f:
        json.dump(token_data, f, indent=2)

    return token_data


def is_token_expired():
    """Check if the current access token is expired"""
    config = load_facebook_config()
    expires_at = config.get('expires_at')

    if not expires_at:
        return True

    try:
        expiry = datetime.fromisoformat(expires_at)
        return datetime.now() >= expiry
    except Exception:
        return True


def get_authorization_url():
    """Generate Facebook OAuth authorization URL"""
    config = load_facebook_config()

    params = {
        "client_id": config['app_id'],
        "redirect_uri": config['redirect_uri'],
        "scope": "business_management,pages_manage_posts,pages_read_engagement,pages_show_list",
        "response_type": "code",
    }

    return f"{FACEBOOK_AUTH_URL}?{urlencode(params)}"


def exchange_code_for_token(authorization_code):
    """Exchange authorization code for access token"""
    config = load_facebook_config()

    params = {
        "client_id": config['app_id'],
        "client_secret": config['app_secret'],
        "redirect_uri": config['redirect_uri'],
        "code": authorization_code,
    }

    response = requests.get(FACEBOOK_TOKEN_URL, params=params, timeout=30)
    response.raise_for_status()

    token_data = response.json()
    short_lived_token = token_data.get('access_token')

    # Exchange for long-lived token
    long_lived = exchange_for_long_lived_token(short_lived_token)
    user_token = long_lived.get('access_token', short_lived_token)
    expires_in = long_lived.get('expires_in', 3600)

    # Get page access token and page info
    page_token = ""
    page_id = config.get('page_id', '')
    instagram_id = config.get('instagram_account_id', '')

    try:
        pages = get_user_pages(user_token)
        if pages:
            first_page = pages[0]
            page_token = first_page.get('access_token', '')
            page_id = page_id or first_page.get('id', '')

            # Try to get Instagram account ID
            if page_id and not instagram_id:
                ig_data = get_instagram_account(page_id, page_token)
                instagram_id = ig_data.get('instagram_account_id', '')
    except Exception as e:
        print(f"[WARN] Could not fetch page/IG data: {e}")

    saved_data = save_facebook_token(
        access_token=user_token,
        page_access_token=page_token,
        page_id=page_id,
        instagram_account_id=instagram_id,
        expires_in=expires_in
    )

    return saved_data


def exchange_for_long_lived_token(short_lived_token):
    """Exchange short-lived token for long-lived token (~60 days)"""
    config = load_facebook_config()

    params = {
        "grant_type": "fb_exchange_token",
        "client_id": config['app_id'],
        "client_secret": config['app_secret'],
        "fb_exchange_token": short_lived_token,
    }

    response = requests.get(FACEBOOK_TOKEN_URL, params=params, timeout=30)
    if response.status_code == 200:
        return response.json()
    return {"access_token": short_lived_token, "expires_in": 3600}


def get_user_pages(user_token):
    """Get list of Facebook Pages the user manages"""
    response = requests.get(
        f"{GRAPH_API_BASE}/me/accounts",
        params={"access_token": user_token},
        timeout=30
    )
    response.raise_for_status()
    return response.json().get('data', [])


def get_instagram_account(page_id, page_token):
    """Get Instagram Business Account ID linked to a Facebook Page"""
    response = requests.get(
        f"{GRAPH_API_BASE}/{page_id}",
        params={
            "fields": "instagram_business_account",
            "access_token": page_token
        },
        timeout=30
    )
    if response.status_code == 200:
        data = response.json()
        ig_account = data.get('instagram_business_account', {})
        return {"instagram_account_id": ig_account.get('id', '')}
    return {"instagram_account_id": ""}


def create_facebook_page_post(message, page_id=None, page_token=None):
    """Create a post on a Facebook Page"""
    config = load_facebook_config()

    if is_token_expired():
        return {"success": False, "error": "Token expired. Please re-authenticate.",
                "authorization_url": get_authorization_url()}

    page_id = page_id or config.get('page_id')
    page_token = page_token or config.get('page_access_token')

    if not page_id or not page_token:
        return {"success": False,
                "error": "Page ID or page access token not configured. Complete OAuth flow first."}

    response = requests.post(
        f"{GRAPH_API_BASE}/{page_id}/feed",
        data={"message": message, "access_token": page_token},
        timeout=30
    )

    if response.status_code == 200:
        result = response.json()
        post_id = result.get('id', '')
        return {
            "success": True,
            "post_id": post_id,
            "post_url": f"https://www.facebook.com/{post_id}",
            "message": "Facebook Page post created successfully"
        }
    else:
        return {
            "success": False,
            "error": f"Facebook API error: {response.status_code}",
            "details": response.text
        }


def create_instagram_media_post(caption, image_url, ig_account_id=None, page_token=None):
    """Create a post on Instagram (requires image_url)"""
    config = load_facebook_config()

    if is_token_expired():
        return {"success": False, "error": "Token expired. Please re-authenticate.",
                "authorization_url": get_authorization_url()}

    ig_account_id = ig_account_id or config.get('instagram_account_id')
    page_token = page_token or config.get('page_access_token')

    if not ig_account_id or not page_token:
        return {"success": False,
                "error": "Instagram account ID or page token not configured. Complete OAuth flow first."}

    # Step 1: Create media container
    container_response = requests.post(
        f"{GRAPH_API_BASE}/{ig_account_id}/media",
        data={
            "image_url": image_url,
            "caption": caption,
            "access_token": page_token
        },
        timeout=30
    )

    if container_response.status_code != 200:
        return {
            "success": False,
            "error": f"Failed to create media container: {container_response.status_code}",
            "details": container_response.text
        }

    container_id = container_response.json().get('id')

    # Step 2: Publish the media container
    publish_response = requests.post(
        f"{GRAPH_API_BASE}/{ig_account_id}/media_publish",
        data={
            "creation_id": container_id,
            "access_token": page_token
        },
        timeout=30
    )

    if publish_response.status_code == 200:
        result = publish_response.json()
        return {
            "success": True,
            "post_id": result.get('id', ''),
            "message": "Instagram post created successfully"
        }
    else:
        return {
            "success": False,
            "error": f"Failed to publish Instagram post: {publish_response.status_code}",
            "details": publish_response.text
        }


def create_draft_post(text, platform="facebook", visibility="PUBLIC", image_url=""):
    """Create a draft post for approval before publishing"""
    draft_dir = Path(VAULT_PATH) / "Pending_Approval" / "Facebook_Drafts"
    draft_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_text = text[:50].replace('\n', ' ').replace('/', '_')
    filename = f"DRAFT_{platform}_{safe_text}_{timestamp}.md"
    filepath = draft_dir / filename

    content = f"""---
type: {platform}_draft
platform: {platform}
visibility: {visibility}
image_url: {image_url}
created: {datetime.now().isoformat()}
status: pending_approval
---

# {platform.title()} Post Draft

## Platform
{platform.title()}

## Content
{text}

## Image URL
{image_url if image_url else 'N/A'}

---
## Approval Instructions
Move this file to `Approved/Facebook_Drafts/` to publish, or `Rejected/Facebook_Drafts/` to discard.
"""

    filepath.write_text(content, encoding='utf-8')

    return {
        "success": True,
        "filepath": str(filepath),
        "filename": filename,
        "message": f"{platform.title()} draft created for approval"
    }


def get_engagement_summary(page_id=None, page_token=None):
    """Get engagement summary for the Facebook Page"""
    config = load_facebook_config()

    page_id = page_id or config.get('page_id')
    page_token = page_token or config.get('page_access_token')

    if not page_id or not page_token:
        return {"success": False, "error": "Page not configured"}

    # Get recent posts with engagement metrics
    response = requests.get(
        f"{GRAPH_API_BASE}/{page_id}/posts",
        params={
            "fields": "message,created_time,likes.summary(true),comments.summary(true),shares",
            "limit": 10,
            "access_token": page_token
        },
        timeout=30
    )

    if response.status_code != 200:
        return {"success": False, "error": f"API error: {response.status_code}",
                "details": response.text}

    posts = response.json().get('data', [])
    total_likes = 0
    total_comments = 0
    total_shares = 0

    post_summaries = []
    for post in posts:
        likes = post.get('likes', {}).get('summary', {}).get('total_count', 0)
        comments = post.get('comments', {}).get('summary', {}).get('total_count', 0)
        shares = post.get('shares', {}).get('count', 0)
        total_likes += likes
        total_comments += comments
        total_shares += shares

        post_summaries.append({
            "id": post.get('id'),
            "message": (post.get('message', '') or '')[:100],
            "created_time": post.get('created_time'),
            "likes": likes,
            "comments": comments,
            "shares": shares
        })

    return {
        "success": True,
        "page_id": page_id,
        "total_posts_analyzed": len(posts),
        "total_likes": total_likes,
        "total_comments": total_comments,
        "total_shares": total_shares,
        "posts": post_summaries,
        "generated_at": datetime.now().isoformat()
    }


# ==================== FLASK ENDPOINTS ====================

@app.route('/capabilities', methods=['GET'])
def get_capabilities():
    """Return the capabilities of this MCP server"""
    config = load_facebook_config()
    capabilities = {
        "name": "facebook-mcp",
        "version": "1.0.0",
        "description": "Facebook/Instagram posting operations for AI Employee",
        "operations": [
            {"name": "create_post", "description": "Create a Facebook Page post",
             "parameters": {"message": {"type": "string"}}},
            {"name": "create_instagram_post", "description": "Create an Instagram post",
             "parameters": {"caption": {"type": "string"}, "image_url": {"type": "string"}}},
            {"name": "create_draft", "description": "Create a draft post for approval",
             "parameters": {"text": {"type": "string"}, "platform": {"type": "string"}}},
            {"name": "get_auth_url", "description": "Get OAuth authorization URL"},
            {"name": "exchange_token", "description": "Exchange auth code for access token"},
            {"name": "get_engagement_summary", "description": "Get engagement metrics summary"},
        ],
        "configured": bool(config.get('app_id') and config.get('app_secret')),
        "authenticated": bool(config.get('page_access_token') and not is_token_expired())
    }
    return jsonify(capabilities)


@app.route('/get_auth_url', methods=['GET'])
def get_auth_url():
    """Get Facebook OAuth authorization URL and redirect to it"""
    config = load_facebook_config()

    if not config.get('app_id'):
        return jsonify({
            "error": "Facebook App ID not configured. Set FACEBOOK_APP_ID in .env",
            "success": False
        }), 400

    auth_url = get_authorization_url()

    # Auto-redirect to Facebook authorization page
    return redirect(auth_url)


@app.route('/callback', methods=['GET'])
def oauth_callback():
    """Handle OAuth callback from Facebook"""
    authorization_code = request.args.get('code', '')
    error = request.args.get('error', '')

    if error:
        return f"""
        <html>
        <head><title>Facebook OAuth Error</title></head>
        <body style="font-family: Arial; max-width: 600px; margin: 50px auto; padding: 20px;">
            <h1 style="color: #d93025;">OAuth Authorization Failed</h1>
            <p>Error: {error}</p>
            <p>Details: {request.args.get('error_description', 'No details')}</p>
            <p><a href="javascript:window.close()">Close this window</a></p>
        </body>
        </html>
        """, 400

    if not authorization_code:
        return f"""
        <html>
        <head><title>Facebook OAuth Error</title></head>
        <body style="font-family: Arial; max-width: 600px; margin: 50px auto; padding: 20px;">
            <h1 style="color: #d93025;">No Authorization Code</h1>
            <p>The authorization code is missing.</p>
        </body>
        </html>
        """, 400

    return f"""
    <html>
    <head><title>Facebook OAuth Success</title></head>
    <body style="font-family: Arial; max-width: 600px; margin: 50px auto; padding: 20px;">
        <h1 style="color: #1877f2;">Facebook Authorization Successful!</h1>
        <p>Your authorization code has been captured.</p>
        <p style="background: #f0f0f0; padding: 10px; border-radius: 5px;">
            <strong>Authorization Code:</strong><br>
            <code style="word-break: break-all;">{authorization_code}</code>
        </p>
        <div id="status" style="color: #666;">Exchanging code for token...</div>
        <script>
            fetch('http://localhost:8006/exchange_token', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{code: '{authorization_code}'}})
            }})
            .then(response => response.json())
            .then(data => {{
                const status = document.getElementById('status');
                if (data.success) {{
                    status.innerHTML = '<strong style="color: green;">Token obtained!</strong><br>' +
                        'Page ID: ' + (data.page_id || 'N/A') + '<br>' +
                        'Instagram ID: ' + (data.instagram_account_id || 'N/A');
                }} else {{
                    status.innerHTML = '<strong style="color: red;">Error:</strong> ' + data.error;
                }}
            }})
            .catch(err => {{
                document.getElementById('status').innerHTML =
                    '<strong style="color: red;">Error:</strong> ' + err.message;
            }});
        </script>
        <p style="margin-top: 30px;"><a href="javascript:window.close()">Close this window</a></p>
    </body>
    </html>
    """


@app.route('/exchange_token', methods=['POST'])
def exchange_token():
    """Exchange authorization code for access token"""
    data = request.json
    authorization_code = data.get('code', '')

    if not authorization_code:
        return jsonify({"error": "Missing authorization code", "success": False}), 400

    try:
        token_data = exchange_code_for_token(authorization_code)

        return jsonify({
            "success": True,
            "message": "Token obtained successfully",
            "expires_at": token_data.get('expires_at'),
            "page_id": token_data.get('page_id'),
            "instagram_account_id": token_data.get('instagram_account_id')
        })

    except Exception as e:
        SECURITY_CONFIG.logger.error(f"Facebook token exchange failed: {str(e)}")
        return jsonify({"error": f"Token exchange failed: {str(e)}", "success": False}), 400


@app.route('/create_post', methods=['POST'])
def create_post():
    """Create a post on a Facebook Page"""
    data = request.json
    message = data.get('message', '') or data.get('text', '')

    if not message:
        return jsonify({"error": "Missing required parameter: message", "success": False}), 400

    try:
        sanitized = SECURITY_CONFIG.sanitize_input(message)
        result = create_facebook_page_post(sanitized)

        if result.get('success'):
            SECURITY_CONFIG.log_action(
                action_type="facebook_post_created",
                actor="claude_code",
                target="facebook",
                parameters={"text_length": len(message), "post_id": result.get('post_id')},
                approval_status="auto_approved",
                result="success"
            )

        return jsonify(result)

    except Exception as e:
        SECURITY_CONFIG.logger.error(f"Error creating Facebook post: {str(e)}")
        return jsonify({"error": str(e), "success": False}), 500


@app.route('/create_instagram_post', methods=['POST'])
def create_ig_post():
    """Create a post on Instagram"""
    data = request.json
    caption = data.get('caption', '') or data.get('text', '')
    image_url = data.get('image_url', '')

    if not caption:
        return jsonify({"error": "Missing required parameter: caption", "success": False}), 400

    if not image_url:
        return jsonify({"error": "Missing required parameter: image_url (Instagram requires an image)",
                        "success": False}), 400

    try:
        sanitized_caption = SECURITY_CONFIG.sanitize_input(caption)
        result = create_instagram_media_post(sanitized_caption, image_url)

        if result.get('success'):
            SECURITY_CONFIG.log_action(
                action_type="instagram_post_created",
                actor="claude_code",
                target="instagram",
                parameters={"caption_length": len(caption), "post_id": result.get('post_id')},
                approval_status="auto_approved",
                result="success"
            )

        return jsonify(result)

    except Exception as e:
        SECURITY_CONFIG.logger.error(f"Error creating Instagram post: {str(e)}")
        return jsonify({"error": str(e), "success": False}), 500


@app.route('/create_draft', methods=['POST'])
def create_draft():
    """Create a draft Facebook/Instagram post for approval"""
    data = request.json
    text = data.get('text', '')
    platform = data.get('platform', 'facebook')
    image_url = data.get('image_url', '')

    if not text:
        return jsonify({"error": "Missing required parameter: text", "success": False}), 400

    if platform not in ('facebook', 'instagram'):
        platform = 'facebook'

    try:
        sanitized = SECURITY_CONFIG.sanitize_input(text)
        result = create_draft_post(sanitized, platform=platform, image_url=image_url)

        SECURITY_CONFIG.log_action(
            action_type=f"{platform}_draft_created",
            actor="claude_code",
            target=platform,
            parameters={"text_length": len(text), "platform": platform},
            approval_status="pending",
            result="success"
        )

        return jsonify(result)

    except Exception as e:
        SECURITY_CONFIG.logger.error(f"Error creating {platform} draft: {str(e)}")
        return jsonify({"error": str(e), "success": False}), 500


@app.route('/check_draft_status', methods=['POST'])
def check_draft_status():
    """Check if a draft post has been approved"""
    data = request.json
    filename = data.get('filename', '')

    draft_dir = Path(VAULT_PATH) / "Pending_Approval" / "Facebook_Drafts"
    approved_dir = Path(VAULT_PATH) / "Approved" / "Facebook_Drafts"
    rejected_dir = Path(VAULT_PATH) / "Rejected" / "Facebook_Drafts"

    if (approved_dir / filename).exists():
        return jsonify({"status": "approved", "location": str(approved_dir / filename)})
    elif (rejected_dir / filename).exists():
        return jsonify({"status": "rejected", "location": str(rejected_dir / filename)})
    elif (draft_dir / filename).exists():
        return jsonify({"status": "pending", "location": str(draft_dir / filename)})
    else:
        return jsonify({"status": "not_found", "message": "Draft not found"}), 404


@app.route('/execute_approved_draft', methods=['POST'])
def execute_approved_draft():
    """Publish an approved draft post"""
    data = request.json
    filename = data.get('filename', '')

    approved_dir = Path(VAULT_PATH) / "Approved" / "Facebook_Drafts"
    approved_file = approved_dir / filename

    if not approved_file.exists():
        return jsonify({"error": "Draft not found in approved directory", "success": False}), 404

    try:
        content = approved_file.read_text(encoding='utf-8')

        # Parse frontmatter
        platform = "facebook"
        post_text = None
        image_url = ""
        lines = content.split('\n')
        in_frontmatter = False
        frontmatter_done = False

        for i, line in enumerate(lines):
            if line.strip() == '---':
                if not in_frontmatter:
                    in_frontmatter = True
                else:
                    frontmatter_done = True
                continue

            if in_frontmatter:
                if line.startswith('platform:'):
                    platform = line.split(':', 1)[1].strip()
                elif line.startswith('image_url:'):
                    image_url = line.split(':', 1)[1].strip()
            elif frontmatter_done and line.startswith('## Content'):
                content_start = i + 1
                post_text = '\n'.join(lines[content_start:]).strip()
                if '---' in post_text:
                    post_text = post_text.split('---')[0].strip()
                # Remove ## Image URL section if present
                if '## Image URL' in post_text:
                    post_text = post_text.split('## Image URL')[0].strip()
                break

        if not post_text:
            return jsonify({"error": "Could not parse draft", "success": False}), 400

        # Publish based on platform
        if platform == "instagram":
            if not image_url:
                return jsonify({"error": "Instagram posts require an image_url",
                                "success": False}), 400
            result = create_instagram_media_post(post_text, image_url)
        else:
            result = create_facebook_page_post(post_text)

        if result.get('success'):
            done_dir = Path(VAULT_PATH) / "Done" / "Facebook_Drafts"
            done_dir.mkdir(parents=True, exist_ok=True)
            approved_file.rename(done_dir / filename)

            SECURITY_CONFIG.log_action(
                action_type=f"{platform}_post_published",
                actor="claude_code",
                target=platform,
                parameters={"post_id": result.get('post_id')},
                approval_status="human_approved",
                result="success"
            )

        return jsonify(result)

    except Exception as e:
        SECURITY_CONFIG.logger.error(f"Error publishing approved draft: {str(e)}")
        return jsonify({"error": str(e), "success": False}), 500


@app.route('/get_engagement_summary', methods=['GET'])
def engagement_summary():
    """Get engagement summary for the Facebook Page"""
    try:
        result = get_engagement_summary()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    config = load_facebook_config()
    return jsonify({
        'status': 'healthy',
        'service': 'facebook-mcp',
        'timestamp': datetime.now().isoformat(),
        'authenticated': bool(config.get('page_access_token') and not is_token_expired())
    })


if __name__ == '__main__':
    config = load_facebook_config()
    print("Facebook/Instagram MCP Server starting on port 8006...")
    print(f"App ID configured: {bool(config.get('app_id'))}")
    print(f"Page token valid: {bool(config.get('page_access_token') and not is_token_expired())}")

    # Ensure directories exist
    Path(VAULT_PATH).mkdir(parents=True, exist_ok=True)
    Path(VAULT_PATH, "Pending_Approval", "Facebook_Drafts").mkdir(parents=True, exist_ok=True)
    Path(VAULT_PATH, "Approved", "Facebook_Drafts").mkdir(parents=True, exist_ok=True)
    Path(VAULT_PATH, "Rejected", "Facebook_Drafts").mkdir(parents=True, exist_ok=True)
    Path(VAULT_PATH, "Done", "Facebook_Drafts").mkdir(parents=True, exist_ok=True)

    print("\nAvailable endpoints:")
    print("  Health:     GET  /health")
    print("  Caps:       GET  /capabilities")
    print("  Auth:       GET  /get_auth_url")
    print("  Callback:   GET  /callback")
    print("  Token:      POST /exchange_token")
    print("  FB Post:    POST /create_post")
    print("  IG Post:    POST /create_instagram_post")
    print("  Draft:      POST /create_draft")
    print("  Check:      POST /check_draft_status")
    print("  Execute:    POST /execute_approved_draft")
    print("  Engagement: GET  /get_engagement_summary")

    app.run(host='localhost', port=8006, debug=False)
