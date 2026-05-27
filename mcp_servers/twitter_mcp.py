"""
Twitter (X) MCP Server
Provides Twitter posting via Twitter API v2 with OAuth 2.0 PKCE + OAuth 1.0a fallback

Port: 8007
"""

import os
import sys
import json
import hashlib
import base64
import secrets
import requests
from pathlib import Path
from flask import Flask, request, jsonify, redirect
from datetime import datetime, timedelta
from urllib.parse import urlencode
from requests_oauthlib import OAuth1

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from security_config import get_security_config
from secure_action_executor import get_secure_executor


app = Flask(__name__)

VAULT_PATH = os.getenv("VAULT_PATH", r"D:\prompteng\AI_Employee_Vault")
SECURITY_CONFIG = get_security_config()
SECURE_EXECUTOR = get_secure_executor()

# Twitter API configuration
TWITTER_API_BASE = "https://api.twitter.com/2"
TWITTER_AUTH_URL = "https://twitter.com/i/oauth2/authorize"
TWITTER_TOKEN_URL = "https://api.twitter.com/2/oauth2/token"

# Twitter configuration
TWITTER_CONFIG = {
    "consumer_key": "",
    "consumer_secret": "",
    "access_token_oauth1": "",
    "access_token_secret": "",
    "bearer_token": "",
    "oauth2_client_id": "",
    "oauth2_client_secret": "",
    "oauth2_access_token": "",
    "oauth2_refresh_token": "",
    "redirect_uri": "http://127.0.0.1:8007/callback",
    "user_id": "",
    "username": "",
    "oauth2_expires_at": None,
}

# PKCE state (in-memory, per-session)
_pkce_state = {
    "code_verifier": "",
    "state": "",
}


def load_twitter_config():
    """Load Twitter configuration from environment or .env file"""
    global TWITTER_CONFIG

    env_file = Path(__file__).parent.parent / '.env'
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    value = value.strip().strip('"').strip("'")
                    if key == 'X_CONSUMER_KEY':
                        TWITTER_CONFIG['consumer_key'] = value
                    elif key == 'X_SECRET_KEY':
                        TWITTER_CONFIG['consumer_secret'] = value
                    elif key == 'X_ACCESS_TOKEN':
                        TWITTER_CONFIG['access_token_oauth1'] = value
                    elif key == 'X_ACCESS_TOKEN_SECRET':
                        TWITTER_CONFIG['access_token_secret'] = value
                    elif key == 'X_BEARER_TOKEN':
                        TWITTER_CONFIG['bearer_token'] = value
                    elif key == 'X_OAUTH2_CLIENT_ID':
                        TWITTER_CONFIG['oauth2_client_id'] = value
                    elif key == 'X_OAUTH2_CLIENT_SECRET':
                        TWITTER_CONFIG['oauth2_client_secret'] = value

    # Load OAuth 2.0 token from file
    token_file = Path(__file__).parent.parent / '.twitter_token.json'
    if token_file.exists():
        try:
            with open(token_file, 'r') as f:
                token_data = json.load(f)
                TWITTER_CONFIG['oauth2_access_token'] = token_data.get('access_token', '')
                TWITTER_CONFIG['oauth2_refresh_token'] = token_data.get('refresh_token', '')
                TWITTER_CONFIG['user_id'] = token_data.get('user_id', '')
                TWITTER_CONFIG['username'] = token_data.get('username', '')
                TWITTER_CONFIG['oauth2_expires_at'] = token_data.get('expires_at')
        except Exception:
            pass

    return TWITTER_CONFIG


def save_twitter_token(access_token, refresh_token="", user_id="",
                       username="", expires_in=7200):
    """Save OAuth 2.0 tokens to file"""
    token_file = Path(__file__).parent.parent / '.twitter_token.json'

    token_data = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user_id": user_id,
        "username": username,
        "expires_at": (datetime.now() + timedelta(seconds=expires_in)).isoformat(),
        "updated": datetime.now().isoformat()
    }

    with open(token_file, 'w') as f:
        json.dump(token_data, f, indent=2)

    return token_data


def get_oauth1():
    """Get OAuth 1.0a authentication object"""
    config = load_twitter_config()
    return OAuth1(
        config['consumer_key'],
        client_secret=config['consumer_secret'],
        resource_owner_key=config['access_token_oauth1'],
        resource_owner_secret=config['access_token_secret'],
    )


def is_oauth2_token_valid():
    """Check if OAuth 2.0 token is valid"""
    config = load_twitter_config()
    if not config.get('oauth2_access_token'):
        return False
    expires_at = config.get('oauth2_expires_at')
    if not expires_at:
        return False
    try:
        return datetime.now() < datetime.fromisoformat(expires_at)
    except Exception:
        return False


def generate_pkce():
    """Generate PKCE code_verifier and code_challenge"""
    global _pkce_state

    code_verifier = secrets.token_urlsafe(64)
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode('ascii')).digest()
    ).rstrip(b'=').decode('ascii')
    state = secrets.token_urlsafe(32)

    _pkce_state['code_verifier'] = code_verifier
    _pkce_state['state'] = state

    return code_verifier, code_challenge, state


def get_authorization_url():
    """Generate Twitter OAuth 2.0 authorization URL with PKCE"""
    config = load_twitter_config()
    _, code_challenge, state = generate_pkce()

    params = {
        "response_type": "code",
        "client_id": config['oauth2_client_id'],
        "redirect_uri": config['redirect_uri'],
        "scope": "tweet.read tweet.write users.read offline.access",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }

    return f"{TWITTER_AUTH_URL}?{urlencode(params)}"


def exchange_code_for_token(authorization_code):
    """Exchange authorization code for OAuth 2.0 access token"""
    config = load_twitter_config()

    data = {
        "grant_type": "authorization_code",
        "code": authorization_code,
        "redirect_uri": config['redirect_uri'],
        "client_id": config['oauth2_client_id'],
        "code_verifier": _pkce_state['code_verifier'],
    }

    auth = (config['oauth2_client_id'], config['oauth2_client_secret'])

    response = requests.post(
        TWITTER_TOKEN_URL,
        data=data,
        auth=auth,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30
    )
    response.raise_for_status()

    token_data = response.json()
    access_token = token_data.get('access_token')
    refresh_token = token_data.get('refresh_token', '')
    expires_in = token_data.get('expires_in', 7200)

    # Get user info with new token
    user_id = ""
    username = ""
    try:
        r = requests.get(
            f"{TWITTER_API_BASE}/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10
        )
        if r.status_code == 200:
            user_data = r.json().get('data', {})
            user_id = user_data.get('id', '')
            username = user_data.get('username', '')
    except Exception:
        pass

    saved_data = save_twitter_token(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user_id,
        username=username,
        expires_in=expires_in
    )

    return saved_data


def refresh_access_token():
    """Refresh OAuth 2.0 access token"""
    config = load_twitter_config()

    if not config.get('oauth2_refresh_token'):
        return {"success": False, "error": "No refresh token available. Re-authenticate."}

    data = {
        "grant_type": "refresh_token",
        "refresh_token": config['oauth2_refresh_token'],
        "client_id": config['oauth2_client_id'],
    }

    auth = (config['oauth2_client_id'], config['oauth2_client_secret'])

    response = requests.post(
        TWITTER_TOKEN_URL,
        data=data,
        auth=auth,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30
    )

    if response.status_code != 200:
        return {"success": False, "error": f"Token refresh failed: {response.status_code}",
                "details": response.text}

    token_data = response.json()
    saved_data = save_twitter_token(
        access_token=token_data.get('access_token'),
        refresh_token=token_data.get('refresh_token', config['oauth2_refresh_token']),
        user_id=config.get('user_id', ''),
        username=config.get('username', ''),
        expires_in=token_data.get('expires_in', 7200)
    )

    return {"success": True, "message": "Token refreshed", "expires_at": saved_data.get('expires_at')}


def get_write_auth():
    """Get authentication for write operations (OAuth 2.0 preferred, OAuth 1.0a fallback)"""
    config = load_twitter_config()

    # Try OAuth 2.0 first
    if is_oauth2_token_valid():
        return {"type": "oauth2", "token": config['oauth2_access_token']}

    # Try refreshing OAuth 2.0 token
    if config.get('oauth2_refresh_token'):
        result = refresh_access_token()
        if result.get('success'):
            config = load_twitter_config()
            return {"type": "oauth2", "token": config['oauth2_access_token']}

    # Fallback to OAuth 1.0a
    if config.get('consumer_key') and config.get('access_token_oauth1'):
        return {"type": "oauth1"}

    return None


def create_tweet(text):
    """Create a tweet using best available auth method"""
    auth_info = get_write_auth()

    if not auth_info:
        return {"success": False, "error": "Not authenticated. Complete OAuth 2.0 flow at /get_auth_url"}

    if len(text) > 280:
        return {"success": False, "error": f"Tweet exceeds 280 character limit ({len(text)} chars)"}

    if auth_info['type'] == 'oauth2':
        response = requests.post(
            f"{TWITTER_API_BASE}/tweets",
            headers={
                "Authorization": f"Bearer {auth_info['token']}",
                "Content-Type": "application/json"
            },
            json={"text": text},
            timeout=30
        )
    else:
        # OAuth 1.0a
        response = requests.post(
            f"{TWITTER_API_BASE}/tweets",
            auth=get_oauth1(),
            json={"text": text},
            timeout=30
        )

    if response.status_code == 201:
        result = response.json()
        tweet_data = result.get('data', {})
        tweet_id = tweet_data.get('id', '')
        config = load_twitter_config()
        username = config.get('username', '')
        return {
            "success": True,
            "tweet_id": tweet_id,
            "tweet_url": f"https://x.com/{username}/status/{tweet_id}" if username else f"https://x.com/i/status/{tweet_id}",
            "auth_method": auth_info['type'],
            "message": "Tweet created successfully"
        }
    else:
        return {
            "success": False,
            "error": f"Twitter API error: {response.status_code}",
            "auth_method": auth_info['type'],
            "details": response.text
        }


def create_draft_tweet(text):
    """Create a draft tweet for approval before publishing"""
    draft_dir = Path(VAULT_PATH) / "Pending_Approval" / "Twitter_Drafts"
    draft_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_text = text[:50].replace('\n', ' ').replace('/', '_')
    filename = f"DRAFT_tweet_{safe_text}_{timestamp}.md"
    filepath = draft_dir / filename

    content = f"""---
type: twitter_draft
created: {datetime.now().isoformat()}
status: pending_approval
char_count: {len(text)}
---

# Twitter Post Draft

## Content
{text}

## Character Count
{len(text)} / 280

---
## Approval Instructions
Move this file to `Approved/Twitter_Drafts/` to publish, or `Rejected/Twitter_Drafts/` to discard.
"""

    filepath.write_text(content, encoding='utf-8')

    return {
        "success": True,
        "filepath": str(filepath),
        "filename": filename,
        "char_count": len(text),
        "message": "Twitter draft created for approval"
    }


def get_engagement_summary():
    """Get engagement summary for recent tweets"""
    config = load_twitter_config()

    # Use OAuth 1.0a for reading
    if config.get('consumer_key') and config.get('access_token_oauth1'):
        auth = get_oauth1()

        try:
            user_info_r = requests.get(f"{TWITTER_API_BASE}/users/me", auth=auth, timeout=10)
            user_info_r.raise_for_status()
            user_data = user_info_r.json().get('data', {})
            user_id = user_data.get('id')
            username = user_data.get('username', '')
        except Exception as e:
            return {"success": False, "error": f"Could not get user info: {e}"}

        response = requests.get(
            f"{TWITTER_API_BASE}/users/{user_id}/tweets",
            auth=auth,
            params={
                "tweet.fields": "public_metrics,created_at",
                "max_results": 10
            },
            timeout=30
        )
    elif is_oauth2_token_valid():
        token = config['oauth2_access_token']
        headers = {"Authorization": f"Bearer {token}"}

        try:
            user_info_r = requests.get(f"{TWITTER_API_BASE}/users/me", headers=headers, timeout=10)
            user_info_r.raise_for_status()
            user_data = user_info_r.json().get('data', {})
            user_id = user_data.get('id')
            username = user_data.get('username', '')
        except Exception as e:
            return {"success": False, "error": f"Could not get user info: {e}"}

        response = requests.get(
            f"{TWITTER_API_BASE}/users/{user_id}/tweets",
            headers=headers,
            params={
                "tweet.fields": "public_metrics,created_at",
                "max_results": 10
            },
            timeout=30
        )
    else:
        return {"success": False, "error": "Not authenticated"}

    if response.status_code != 200:
        return {"success": False, "error": f"API error: {response.status_code}",
                "details": response.text}

    tweets = response.json().get('data', [])
    total_likes = 0
    total_retweets = 0
    total_replies = 0
    total_impressions = 0

    tweet_summaries = []
    for tweet in tweets:
        metrics = tweet.get('public_metrics', {})
        likes = metrics.get('like_count', 0)
        retweets = metrics.get('retweet_count', 0)
        replies = metrics.get('reply_count', 0)
        impressions = metrics.get('impression_count', 0)

        total_likes += likes
        total_retweets += retweets
        total_replies += replies
        total_impressions += impressions

        tweet_summaries.append({
            "id": tweet.get('id'),
            "text": tweet.get('text', '')[:100],
            "created_at": tweet.get('created_at'),
            "likes": likes,
            "retweets": retweets,
            "replies": replies,
            "impressions": impressions
        })

    return {
        "success": True,
        "username": username,
        "total_tweets_analyzed": len(tweets),
        "total_likes": total_likes,
        "total_retweets": total_retweets,
        "total_replies": total_replies,
        "total_impressions": total_impressions,
        "tweets": tweet_summaries,
        "generated_at": datetime.now().isoformat()
    }


# ==================== FLASK ENDPOINTS ====================

@app.route('/capabilities', methods=['GET'])
def get_capabilities():
    """Return the capabilities of this MCP server"""
    config = load_twitter_config()
    capabilities = {
        "name": "twitter-mcp",
        "version": "2.0.0",
        "description": "Twitter (X) posting via OAuth 2.0 PKCE + OAuth 1.0a fallback",
        "operations": [
            {"name": "create_tweet", "description": "Create a tweet (max 280 chars)"},
            {"name": "create_draft", "description": "Create a draft tweet for approval"},
            {"name": "get_auth_url", "description": "Start OAuth 2.0 PKCE flow"},
            {"name": "verify_credentials", "description": "Verify credentials and get user info"},
            {"name": "get_engagement_summary", "description": "Get engagement metrics"},
        ],
        "oauth2_configured": bool(config.get('oauth2_client_id')),
        "oauth2_authenticated": is_oauth2_token_valid(),
        "oauth1_configured": bool(config.get('consumer_key') and config.get('access_token_oauth1')),
        "max_tweet_length": 280
    }
    return jsonify(capabilities)


@app.route('/get_auth_url', methods=['GET'])
def get_auth_url():
    """Redirect to Twitter OAuth 2.0 authorization"""
    config = load_twitter_config()

    if not config.get('oauth2_client_id'):
        return jsonify({
            "error": "OAuth 2.0 Client ID not configured. Set X_OAUTH2_CLIENT_ID in .env",
            "success": False
        }), 400

    auth_url = get_authorization_url()
    return redirect(auth_url)


@app.route('/callback', methods=['GET'])
def oauth_callback():
    """Handle OAuth 2.0 callback from Twitter"""
    authorization_code = request.args.get('code', '')
    state = request.args.get('state', '')
    error = request.args.get('error', '')

    if error:
        return f"""
        <html><body style="font-family: Arial; max-width: 600px; margin: 50px auto; padding: 20px;">
            <h1 style="color: #d93025;">OAuth Error</h1>
            <p>Error: {error}</p>
        </body></html>
        """, 400

    if state != _pkce_state.get('state'):
        return f"""
        <html><body style="font-family: Arial; max-width: 600px; margin: 50px auto; padding: 20px;">
            <h1 style="color: #d93025;">State Mismatch</h1>
            <p>OAuth state does not match. Try again from /get_auth_url</p>
        </body></html>
        """, 400

    if not authorization_code:
        return f"""
        <html><body style="font-family: Arial; max-width: 600px; margin: 50px auto; padding: 20px;">
            <h1 style="color: #d93025;">No Authorization Code</h1>
            <p>The authorization code is missing.</p>
        </body></html>
        """, 400

    # Exchange code for token immediately
    try:
        token_data = exchange_code_for_token(authorization_code)
        username = token_data.get('username', 'Unknown')
        expires = token_data.get('expires_at', 'Unknown')

        return f"""
        <html><body style="font-family: Arial; max-width: 600px; margin: 50px auto; padding: 20px;">
            <h1 style="color: #1da1f2;">Twitter Authorization Successful!</h1>
            <p><strong>Username:</strong> @{username}</p>
            <p><strong>Expires:</strong> {expires}</p>
            <p style="color: green; font-weight: bold;">Token saved. You can now post tweets!</p>
        </body></html>
        """
    except Exception as e:
        return f"""
        <html><body style="font-family: Arial; max-width: 600px; margin: 50px auto; padding: 20px;">
            <h1 style="color: #d93025;">Token Exchange Failed</h1>
            <p>Error: {str(e)}</p>
        </body></html>
        """, 400


@app.route('/verify_credentials', methods=['GET'])
def verify_credentials():
    """Verify credentials and return user info"""
    config = load_twitter_config()

    # Try OAuth 1.0a
    if config.get('consumer_key') and config.get('access_token_oauth1'):
        try:
            auth = get_oauth1()
            r = requests.get(f"{TWITTER_API_BASE}/users/me", auth=auth, timeout=10)
            if r.status_code == 200:
                user_data = r.json().get('data', {})
                return jsonify({
                    "success": True,
                    "auth_method": "OAuth 1.0a",
                    "user_id": user_data.get('id'),
                    "username": user_data.get('username'),
                    "name": user_data.get('name'),
                    "message": f"Authenticated as @{user_data.get('username')}"
                })
        except Exception:
            pass

    # Try OAuth 2.0
    if is_oauth2_token_valid():
        try:
            r = requests.get(
                f"{TWITTER_API_BASE}/users/me",
                headers={"Authorization": f"Bearer {config['oauth2_access_token']}"},
                timeout=10
            )
            if r.status_code == 200:
                user_data = r.json().get('data', {})
                return jsonify({
                    "success": True,
                    "auth_method": "OAuth 2.0",
                    "user_id": user_data.get('id'),
                    "username": user_data.get('username'),
                    "name": user_data.get('name'),
                    "message": f"Authenticated as @{user_data.get('username')}"
                })
        except Exception:
            pass

    return jsonify({
        "success": False,
        "error": "No valid credentials. Complete OAuth 2.0 flow at /get_auth_url",
        "oauth2_configured": bool(config.get('oauth2_client_id')),
        "oauth1_configured": bool(config.get('consumer_key') and config.get('access_token_oauth1')),
    }), 400


@app.route('/create_tweet', methods=['POST'])
def create_tweet_endpoint():
    """Create a tweet on Twitter"""
    data = request.json
    text = data.get('text', '')

    if not text:
        return jsonify({"error": "Missing required parameter: text", "success": False}), 400

    if len(text) > 280:
        return jsonify({
            "error": f"Tweet exceeds 280 character limit ({len(text)} chars)",
            "success": False
        }), 400

    try:
        sanitized = SECURITY_CONFIG.sanitize_input(text)
        result = create_tweet(sanitized)

        if result.get('success'):
            SECURITY_CONFIG.log_action(
                action_type="tweet_created",
                actor="claude_code",
                target="twitter",
                parameters={"char_count": len(text), "tweet_id": result.get('tweet_id')},
                approval_status="auto_approved",
                result="success"
            )

        return jsonify(result)

    except Exception as e:
        SECURITY_CONFIG.logger.error(f"Error creating tweet: {str(e)}")
        return jsonify({"error": str(e), "success": False}), 500


@app.route('/create_draft', methods=['POST'])
def create_draft():
    """Create a draft tweet for approval"""
    data = request.json
    text = data.get('text', '')

    if not text:
        return jsonify({"error": "Missing required parameter: text", "success": False}), 400

    if len(text) > 280:
        return jsonify({
            "error": f"Tweet exceeds 280 character limit ({len(text)} chars)",
            "success": False
        }), 400

    try:
        sanitized = SECURITY_CONFIG.sanitize_input(text)
        result = create_draft_tweet(sanitized)

        SECURITY_CONFIG.log_action(
            action_type="twitter_draft_created",
            actor="claude_code",
            target="twitter",
            parameters={"char_count": len(text)},
            approval_status="pending",
            result="success"
        )

        return jsonify(result)

    except Exception as e:
        SECURITY_CONFIG.logger.error(f"Error creating Twitter draft: {str(e)}")
        return jsonify({"error": str(e), "success": False}), 500


@app.route('/check_draft_status', methods=['POST'])
def check_draft_status():
    """Check if a draft tweet has been approved"""
    data = request.json
    filename = data.get('filename', '')

    draft_dir = Path(VAULT_PATH) / "Pending_Approval" / "Twitter_Drafts"
    approved_dir = Path(VAULT_PATH) / "Approved" / "Twitter_Drafts"
    rejected_dir = Path(VAULT_PATH) / "Rejected" / "Twitter_Drafts"

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
    """Publish an approved draft tweet"""
    data = request.json
    filename = data.get('filename', '')

    approved_dir = Path(VAULT_PATH) / "Approved" / "Twitter_Drafts"
    approved_file = approved_dir / filename

    if not approved_file.exists():
        return jsonify({"error": "Draft not found in approved directory", "success": False}), 404

    try:
        content = approved_file.read_text(encoding='utf-8')

        post_text = None
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

            if frontmatter_done and line.startswith('## Content'):
                content_start = i + 1
                post_text = '\n'.join(lines[content_start:]).strip()
                if '## Character Count' in post_text:
                    post_text = post_text.split('## Character Count')[0].strip()
                if '---' in post_text:
                    post_text = post_text.split('---')[0].strip()
                break

        if not post_text:
            return jsonify({"error": "Could not parse draft", "success": False}), 400

        result = create_tweet(post_text)

        if result.get('success'):
            done_dir = Path(VAULT_PATH) / "Done" / "Twitter_Drafts"
            done_dir.mkdir(parents=True, exist_ok=True)
            approved_file.rename(done_dir / filename)

            SECURITY_CONFIG.log_action(
                action_type="tweet_published",
                actor="claude_code",
                target="twitter",
                parameters={"tweet_id": result.get('tweet_id')},
                approval_status="human_approved",
                result="success"
            )

        return jsonify(result)

    except Exception as e:
        SECURITY_CONFIG.logger.error(f"Error publishing approved tweet: {str(e)}")
        return jsonify({"error": str(e), "success": False}), 500


@app.route('/get_engagement_summary', methods=['GET'])
def engagement_summary():
    """Get engagement summary for recent tweets"""
    try:
        result = get_engagement_summary()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    config = load_twitter_config()
    return jsonify({
        'status': 'healthy',
        'service': 'twitter-mcp',
        'timestamp': datetime.now().isoformat(),
        'oauth1_configured': bool(config.get('consumer_key') and config.get('access_token_oauth1')),
        'oauth2_configured': bool(config.get('oauth2_client_id')),
        'oauth2_authenticated': is_oauth2_token_valid(),
    })


if __name__ == '__main__':
    config = load_twitter_config()
    print("Twitter (X) MCP Server starting on port 8007...")
    print(f"OAuth 1.0a configured: {bool(config.get('consumer_key') and config.get('access_token_oauth1'))}")
    print(f"OAuth 2.0 configured: {bool(config.get('oauth2_client_id'))}")
    print(f"OAuth 2.0 token valid: {is_oauth2_token_valid()}")

    # Ensure directories exist
    Path(VAULT_PATH).mkdir(parents=True, exist_ok=True)
    Path(VAULT_PATH, "Pending_Approval", "Twitter_Drafts").mkdir(parents=True, exist_ok=True)
    Path(VAULT_PATH, "Approved", "Twitter_Drafts").mkdir(parents=True, exist_ok=True)
    Path(VAULT_PATH, "Rejected", "Twitter_Drafts").mkdir(parents=True, exist_ok=True)
    Path(VAULT_PATH, "Done", "Twitter_Drafts").mkdir(parents=True, exist_ok=True)

    print("\nAvailable endpoints:")
    print("  Health:     GET  /health")
    print("  Caps:       GET  /capabilities")
    print("  Auth:       GET  /get_auth_url  (OAuth 2.0 PKCE flow)")
    print("  Callback:   GET  /callback")
    print("  Verify:     GET  /verify_credentials")
    print("  Tweet:      POST /create_tweet")
    print("  Draft:      POST /create_draft")
    print("  Check:      POST /check_draft_status")
    print("  Execute:    POST /execute_approved_draft")
    print("  Engagement: GET  /get_engagement_summary")

    app.run(host='localhost', port=8007, debug=False)
