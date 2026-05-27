"""
LinkedIn MCP Server
Provides LinkedIn posting capabilities via LinkedIn API v2
"""

import os
import sys
import json
import base64
import requests
from pathlib import Path
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
from urllib.parse import quote

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import security modules
from security_config import get_security_config
from secure_action_executor import get_secure_executor


app = Flask(__name__)

VAULT_PATH = os.getenv("VAULT_PATH", r"D:\prompteng\AI_Employee_Vault")
SECURITY_CONFIG = get_security_config()
SECURE_EXECUTOR = get_secure_executor()

# LinkedIn API configuration
LINKEDIN_API_BASE = "https://api.linkedin.com/v2"
LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"

# LinkedIn configuration
LINKEDIN_CONFIG = {
    "client_id": "",
    "client_secret": "",
    "redirect_uri": "http://localhost:8002/callback",
    "access_token": "",
    "expires_at": None,
    "person_urn": ""  # LinkedIn Person URN (e.g., urn:li:person:ABC123)
}


def load_linkedin_config():
    """Load LinkedIn configuration from environment or config file"""
    global LINKEDIN_CONFIG

    # Try loading from .env file
    env_file = Path(__file__).parent.parent / '.env'
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    value = value.strip().strip('"').strip("'")
                    if key == 'LINKEDIN_CLIENT_ID':
                        LINKEDIN_CONFIG['client_id'] = value
                    elif key == 'LINKEDIN_CLIENT_SECRET':
                        LINKEDIN_CONFIG['client_secret'] = value
                    elif key == 'LINKEDIN_REDIRECT_URI':
                        LINKEDIN_CONFIG['redirect_uri'] = value
                    elif key == 'LINKEDIN_ACCESS_TOKEN':
                        LINKEDIN_CONFIG['access_token'] = value
                    elif key == 'LINKEDIN_PERSON_URN':
                        LINKEDIN_CONFIG['person_urn'] = value

    # Check for token file
    token_file = Path(__file__).parent.parent / '.linkedin_token.json'
    if token_file.exists():
        try:
            with open(token_file, 'r') as f:
                token_data = json.load(f)
                LINKEDIN_CONFIG['access_token'] = token_data.get('access_token', '')
                LINKEDIN_CONFIG['expires_at'] = token_data.get('expires_at')
                # Only update person_urn from token file if not already set from .env
                if not LINKEDIN_CONFIG['person_urn'] and token_data.get('person_urn'):
                    LINKEDIN_CONFIG['person_urn'] = token_data.get('person_urn', '')
        except Exception:
            pass

    return LINKEDIN_CONFIG


def save_linkedin_token(access_token, expires_in, person_urn=""):
    """Save LinkedIn access token to file"""
    token_file = Path(__file__).parent.parent / '.linkedin_token.json'
    
    token_data = {
        "access_token": access_token,
        "expires_at": (datetime.now() + timedelta(seconds=expires_in)).isoformat(),
        "person_urn": person_urn,
        "updated": datetime.now().isoformat()
    }
    
    with open(token_file, 'w') as f:
        json.dump(token_data, f, indent=2)
    
    return token_data


def is_token_expired():
    """Check if the current access token is expired"""
    config = load_linkedin_config()
    expires_at = config.get('expires_at')
    
    if not expires_at:
        return True
    
    try:
        expiry = datetime.fromisoformat(expires_at)
        return datetime.now() >= expiry
    except Exception:
        return True


def get_authorization_url():
    """Generate LinkedIn OAuth authorization URL"""
    config = load_linkedin_config()

    # URL encode the redirect_uri parameter
    redirect_uri_encoded = quote(config['redirect_uri'], safe='')
    
    # URL encode the scope parameter (spaces become %20)
    # Using OpenID Connect scopes (openid, profile, email) + w_member_social for posting
    # The ID token's "sub" claim gives us the Member ID - no need for r_liteprofile
    scope_encoded = quote("openid profile email w_member_social", safe='')

    params = {
        "response_type": "code",
        "client_id": config['client_id'],
        "redirect_uri": redirect_uri_encoded,
        "scope": scope_encoded
    }

    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    return f"{LINKEDIN_AUTH_URL}?{query_string}"


def exchange_code_for_token(authorization_code):
    """Exchange authorization code for access token"""
    config = load_linkedin_config()

    data = {
        "grant_type": "authorization_code",
        "code": authorization_code,
        "redirect_uri": config['redirect_uri'],
        "client_id": config['client_id'],
        "client_secret": config['client_secret']
    }

    response = requests.post(LINKEDIN_TOKEN_URL, data=data, timeout=30)
    response.raise_for_status()

    token_data = response.json()
    access_token = token_data.get('access_token')
    expires_in = token_data.get('expires_in', 3600)
    id_token = token_data.get('id_token')

    # Get person URN from ID token (OpenID Connect)
    person_urn = ""
    if id_token:
        try:
            person_urn = get_person_urn_from_id_token(id_token)
            print(f"[DEBUG] Person URN from ID token: {person_urn}")
        except Exception as e:
            print(f"[DEBUG] Could not extract URN from ID token: {e}")
    
    # Fallback: Try /me endpoint if ID token didn't work
    if not person_urn:
        try:
            person_urn = get_person_urn(access_token)
            print(f"[DEBUG] Person URN from /me endpoint: {person_urn}")
        except Exception as e:
            print(f"[DEBUG] Could not get person URN from /me: {e}")
            person_urn = ""

    # Save token
    saved_data = save_linkedin_token(access_token, expires_in, person_urn)

    return saved_data


def get_person_urn_from_id_token(id_token):
    """Extract Person URN from OpenID Connect ID token"""
    try:
        import base64
        import json
        
        # ID token is JWT: header.payload.signature
        # We need to decode the payload (second part)
        parts = id_token.split('.')
        if len(parts) != 3:
            raise ValueError("Invalid JWT format")
        
        # Decode payload (add padding if needed)
        payload = parts[1]
        # Add padding if needed
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += '=' * padding
        
        # URL-safe base64 decode
        decoded = base64.urlsafe_b64decode(payload)
        claims = json.loads(decoded)
        
        # Extract sub claim (LinkedIn Member ID)
        sub = claims.get('sub', '')
        if not sub:
            raise ValueError("No 'sub' claim in ID token")
        
        # Build Person URN
        person_urn = f"urn:li:person:{sub}"
        print(f"[DEBUG] ID token claims: {list(claims.keys())}")
        print(f"[DEBUG] sub claim: {sub}")
        
        return person_urn
        
    except Exception as e:
        print(f"[DEBUG] ID token decode error: {e}")
        raise


def get_person_urn(access_token):
    """Get the authenticated user's LinkedIn Person URN"""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Restli-Protocol-Version": "2.0.0",
        "LinkedIn-Version": "202402"
    }

    print(f"[DEBUG] Calling /me endpoint to get Person URN...")
    response = requests.get(
        f"{LINKEDIN_API_BASE}/me",
        headers=headers,
        timeout=10
    )
    print(f"[DEBUG] /me response status: {response.status_code}")
    print(f"[DEBUG] /me response body: {response.text}")
    
    if response.status_code == 200:
        profile = response.json()
        person_id = profile.get('id', '')
        print(f"[DEBUG] Person ID from /me: {person_id}")
        # Return in urn:li:person:{id} format
        return f"urn:li:person:{person_id}" if person_id else ''
    
    response.raise_for_status()
    return ''


def refresh_access_token():
    """Refresh the access token if needed"""
    # LinkedIn uses short-lived tokens; re-authentication may be required
    # For now, we'll just indicate that re-auth is needed
    return {
        "requires_reauth": True,
        "authorization_url": get_authorization_url()
    }


def create_linkedin_post(text, visibility="PUBLIC", images=None):
    """Create a post on LinkedIn"""
    config = load_linkedin_config()

    if is_token_expired():
        return refresh_access_token()

    access_token = config['access_token']
    person_urn = config['person_urn']

    # Try to get person URN if not available
    if not person_urn:
        try:
            person_urn = get_person_urn(access_token)
        except Exception:
            person_urn = None

    # If we still don't have URN, try to find it from a different endpoint
    if not person_urn:
        # Try using the vanityName endpoint which may work with just w_member_social
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "X-Restli-Protocol-Version": "2.0.0"
            }
            # Try to get user info from a different endpoint
            response = requests.get(
                "https://api.linkedin.com/v2/projection?action=edges",
                headers=headers,
                timeout=10
            )
            # This is a fallback - main approach is to get URN from token introspection
        except Exception:
            pass
        
        # For now, we need to manually get the person URN
        # User can get it from LinkedIn URL: linkedin.com/in/your-name
        # Or from the debug endpoint after manual lookup
        return {
            "success": False,
            "error": "Person URN not available. Please re-authenticate with proper scopes or manually set LINKEDIN_PERSON_URN in .env file",
            "hint": "Your Person URN can be found from your LinkedIn profile URL or by using LinkedIn's API explorer"
        }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json"
    }

    # Build post data - use person URN format (LinkedIn accepts both person and member formats)
    # Use urn:li:person:{id} format which works with OpenID Connect
    if person_urn.startswith('urn:li:person:'):
        author_urn = person_urn  # Use as-is
    elif person_urn.startswith('urn:li:member:'):
        author_urn = person_urn
    else:
        # Assume it's just the numeric ID, use person format
        author_urn = f"urn:li:person:{person_urn}"

    print(f"[DEBUG] Author URN for post: {author_urn}")
    
    post_data = {
        "author": author_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {
                    "text": text
                },
                "shareMediaCategory": "NONE"
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": visibility
        }
    }

    print(f"[DEBUG] Post payload: {json.dumps(post_data, indent=2)}")

    # Handle images (future enhancement)
    if images:
        post_data["specificContent"]["com.linkedin.ugc.ShareContent"]["shareMediaCategory"] = "IMAGE"
        # Media upload would require additional API calls

    print(f"[DEBUG] Posting to {LINKEDIN_API_BASE}/ugcPosts")
    response = requests.post(
        f"{LINKEDIN_API_BASE}/ugcPosts",
        headers=headers,
        json=post_data,
        timeout=30
    )

    print(f"[DEBUG] Post response status: {response.status_code}")
    print(f"[DEBUG] Post response body: {response.text}")

    if response.status_code == 201:
        result = response.json()
        post_id = result.get('id', '')
        return {
            "success": True,
            "post_id": post_id,
            "post_url": f"https://www.linkedin.com/feed/update/{post_id.replace(':', '_')}",
            "message": "Post created successfully"
        }
    else:
        return {
            "success": False,
            "error": f"LinkedIn API error: {response.status_code}",
            "details": response.text
        }


def create_draft_post(text, visibility="PUBLIC"):
    """Create a draft post for approval before publishing"""
    draft_dir = Path(VAULT_PATH) / "Pending_Approval" / "LinkedIn_Drafts"
    draft_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_text = text[:50].replace('\n', ' ').replace('/', '_')
    filename = f"DRAFT_{safe_text}_{timestamp}.md"
    filepath = draft_dir / filename
    
    content = f"""---
type: linkedin_draft
visibility: {visibility}
created: {datetime.now().isoformat()}
status: pending_approval
---

# LinkedIn Post Draft

## Visibility
{visibility}

## Content
{text}

---
## Approval Instructions
Move this file to `Approved/LinkedIn_Drafts/` to publish, or `Rejected/LinkedIn_Drafts/` to discard.
"""
    
    filepath.write_text(content, encoding='utf-8')
    
    return {
        "success": True,
        "filepath": str(filepath),
        "message": "LinkedIn draft created for approval"
    }


@app.route('/capabilities', methods=['GET'])
def get_capabilities():
    """Return the capabilities of this MCP server"""
    config = load_linkedin_config()
    capabilities = {
        "name": "linkedin-mcp",
        "version": "1.0.0",
        "description": "LinkedIn posting operations for AI Employee",
        "operations": [
            {
                "name": "create_post",
                "description": "Create a post on LinkedIn",
                "parameters": {
                    "text": {"type": "string", "description": "Post content"},
                    "visibility": {"type": "string", "description": "PUBLIC or CONNECTIONS_ONLY"},
                    "images": {"type": "array", "description": "List of image URLs or paths"}
                }
            },
            {
                "name": "create_draft",
                "description": "Create a draft post (requires approval before publishing)",
                "parameters": {
                    "text": {"type": "string", "description": "Post content"},
                    "visibility": {"type": "string", "description": "PUBLIC or CONNECTIONS_ONLY"}
                }
            },
            {
                "name": "get_auth_url",
                "description": "Get OAuth authorization URL for LinkedIn",
                "parameters": {}
            }
        ],
        "configured": bool(config.get('client_id') and config.get('client_secret')),
        "authenticated": bool(config.get('access_token') and not is_token_expired())
    }
    return jsonify(capabilities)


@app.route('/get_auth_url', methods=['GET'])
def get_auth_url():
    """Get LinkedIn OAuth authorization URL"""
    config = load_linkedin_config()

    if not config.get('client_id'):
        return jsonify({
            "error": "LinkedIn client ID not configured",
            "success": False
        }), 400

    auth_url = get_authorization_url()

    return jsonify({
        "success": True,
        "authorization_url": auth_url,
        "redirect_uri": config['redirect_uri'],
        "instructions": "Open this URL in a browser, authorize, and copy the authorization code from the redirect URL"
    })


@app.route('/debug_redirect_uri', methods=['GET'])
def debug_redirect_uri():
    """Debug endpoint to verify redirect URI configuration"""
    config = load_linkedin_config()
    
    redirect_uri = config.get('redirect_uri', '')
    redirect_uri_encoded = quote(redirect_uri, safe='')
    
    return jsonify({
        "redirect_uri_raw": redirect_uri,
        "redirect_uri_encoded": redirect_uri_encoded,
        "redirect_uri_length": len(redirect_uri),
        "redirect_uri_bytes": [ord(c) for c in redirect_uri],
        "client_id": config.get('client_id', ''),
        "client_secret_configured": bool(config.get('client_secret')),
        "full_auth_url": get_authorization_url()
    })


@app.route('/callback', methods=['GET'])
def oauth_callback():
    """Handle OAuth callback from LinkedIn"""
    authorization_code = request.args.get('code', '')
    error = request.args.get('error', '')

    if error:
        return f"""
        <html>
        <head><title>LinkedIn OAuth Error</title></head>
        <body style="font-family: Arial; max-width: 600px; margin: 50px auto; padding: 20px;">
            <h1 style="color: #d93025;">OAuth Authorization Failed</h1>
            <p>Error: {error}</p>
            <p>Error Details: {request.args.get('error_description', 'No details')}</p>
            <p><a href="javascript:window.close()">Close this window</a> and try again.</p>
        </body>
        </html>
        """, 400

    if not authorization_code:
        return f"""
        <html>
        <head><title>LinkedIn OAuth Error</title></head>
        <body style="font-family: Arial; max-width: 600px; margin: 50px auto; padding: 20px;">
            <h1 style="color: #d93025;">No Authorization Code Received</h1>
            <p>The authorization code is missing from the callback URL.</p>
            <p><a href="javascript:window.close()">Close this window</a> and try again.</p>
        </body>
        </html>
        """, 400

    # Return success page with code
    return f"""
    <html>
    <head><title>LinkedIn OAuth Success</title></head>
    <body style="font-family: Arial; max-width: 600px; margin: 50px auto; padding: 20px;">
        <h1 style="color: #0a66c2;">LinkedIn Authorization Successful!</h1>
        <p>Your authorization code has been captured.</p>
        <p style="background: #f0f0f0; padding: 10px; border-radius: 5px;">
            <strong>Authorization Code:</strong><br>
            <code style="word-break: break-all;">{authorization_code}</code>
        </p>
        <p>The MCP server will now exchange this code for an access token...</p>
        <div id="status" style="color: #666;">Processing...</div>
        <script>
            // Auto-submit the code to the exchange_token endpoint
            fetch('http://localhost:8002/exchange_token', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{code: '{authorization_code}'}})
            }})
            .then(response => response.json())
            .then(data => {{
                const status = document.getElementById('status');
                if (data.success) {{
                    status.innerHTML = '<strong style="color: green;">✓ Token obtained successfully!</strong><br>' +
                        'Expires: ' + data.expires_at + '<br>' +
                        'Person URN: ' + data.person_urn;
                }} else {{
                    status.innerHTML = '<strong style="color: red;">✗ Error:</strong> ' + data.error;
                }}
            }})
            .catch(err => {{
                document.getElementById('status').innerHTML = 
                    '<strong style="color: red;">✗ Error:</strong> ' + err.message;
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
        return jsonify({
            "error": "Missing authorization code",
            "success": False
        }), 400

    try:
        token_data = exchange_code_for_token(authorization_code)

        return jsonify({
            "success": True,
            "message": "Token obtained successfully",
            "expires_at": token_data.get('expires_at'),
            "person_urn": token_data.get('person_urn')
        })

    except Exception as e:
        SECURITY_CONFIG.logger.error(f"Token exchange failed: {str(e)}")
        return jsonify({
            "error": f"Token exchange failed: {str(e)}",
            "success": False
        }), 400


@app.route('/create_post', methods=['POST'])
def create_post():
    """Create a post on LinkedIn"""
    data = request.json
    
    text = data.get('text', '')
    visibility = data.get('visibility', 'PUBLIC')
    images = data.get('images', [])
    
    # Validate inputs
    if not text:
        return jsonify({
            "error": "Missing required parameter: text",
            "success": False
        }), 400
    
    if len(text) > 3000:
        return jsonify({
            "error": "Post text exceeds 3000 character limit",
            "success": False
        }), 400
    
    # Validate visibility
    if visibility not in ['PUBLIC', 'CONNECTIONS_ONLY']:
        visibility = 'PUBLIC'
    
    try:
        # Sanitize inputs
        sanitized_text = SECURITY_CONFIG.sanitize_input(text)
        
        # Create the post
        result = create_linkedin_post(sanitized_text, visibility, images)
        
        if result.get('success'):
            # Log the post creation
            SECURITY_CONFIG.log_action(
                action_type="linkedin_post_created",
                actor="claude_code",
                target="linkedin",
                parameters={
                    "text_length": len(text),
                    "visibility": visibility,
                    "post_id": result.get('post_id')
                },
                approval_status="auto_approved",
                result="success"
            )
        else:
            SECURITY_CONFIG.logger.error(f"LinkedIn post failed: {result.get('error')}")
        
        return jsonify(result)
    
    except Exception as e:
        SECURITY_CONFIG.logger.error(f"Unexpected error creating LinkedIn post: {str(e)}")
        return jsonify({"error": str(e), "success": False}), 500


@app.route('/create_draft', methods=['POST'])
def create_draft():
    """Create a draft LinkedIn post for approval before publishing"""
    data = request.json
    
    text = data.get('text', '')
    visibility = data.get('visibility', 'PUBLIC')
    
    # Validate inputs
    if not text:
        return jsonify({
            "error": "Missing required parameter: text",
            "success": False
        }), 400
    
    if len(text) > 3000:
        return jsonify({
            "error": "Post text exceeds 3000 character limit",
            "success": False
        }), 400
    
    # Validate visibility
    if visibility not in ['PUBLIC', 'CONNECTIONS_ONLY']:
        visibility = 'PUBLIC'
    
    try:
        # Sanitize inputs
        sanitized_text = SECURITY_CONFIG.sanitize_input(text)
        
        # Create draft
        result = create_draft_post(sanitized_text, visibility)
        
        # Log the draft creation
        SECURITY_CONFIG.log_action(
            action_type="linkedin_draft_created",
            actor="claude_code",
            target="linkedin",
            parameters={"text_length": len(text), "visibility": visibility},
            approval_status="pending",
            result="success"
        )
        
        return jsonify(result)
    
    except Exception as e:
        SECURITY_CONFIG.logger.error(f"Error creating LinkedIn draft: {str(e)}")
        return jsonify({"error": str(e), "success": False}), 500


@app.route('/check_draft_status', methods=['POST'])
def check_draft_status():
    """Check if a draft post has been approved"""
    data = request.json
    filename = data.get('filename', '')
    
    draft_dir = Path(VAULT_PATH) / "Pending_Approval" / "LinkedIn_Drafts"
    approved_dir = Path(VAULT_PATH) / "Approved" / "LinkedIn_Drafts"
    rejected_dir = Path(VAULT_PATH) / "Rejected" / "LinkedIn_Drafts"
    
    pending_file = draft_dir / filename
    approved_file = approved_dir / filename
    rejected_file = rejected_dir / filename
    
    if approved_file.exists():
        return jsonify({"status": "approved", "location": str(approved_file)})
    elif rejected_file.exists():
        return jsonify({"status": "rejected", "location": str(rejected_file)})
    elif pending_file.exists():
        return jsonify({"status": "pending", "location": str(pending_file)})
    else:
        return jsonify({"status": "not_found", "message": "Draft not found"}), 404


@app.route('/execute_approved_draft', methods=['POST'])
def execute_approved_draft():
    """Publish an approved draft LinkedIn post"""
    data = request.json
    filename = data.get('filename', '')
    
    approved_dir = Path(VAULT_PATH) / "Approved" / "LinkedIn_Drafts"
    approved_file = approved_dir / filename
    
    if not approved_file.exists():
        return jsonify({
            "error": "Draft not found in approved directory",
            "success": False
        }), 404
    
    try:
        # Parse the draft file
        content = approved_file.read_text(encoding='utf-8')
        
        # Extract post details from frontmatter and content
        visibility = "PUBLIC"
        post_text = None
        lines = content.split('\n')
        in_frontmatter = False
        frontmatter_done = False
        in_content = False
        
        for i, line in enumerate(lines):
            if line.strip() == '---':
                if not in_frontmatter:
                    in_frontmatter = True
                else:
                    frontmatter_done = True
                continue
            
            if in_frontmatter:
                if line.startswith('visibility:'):
                    visibility = line.split(':', 1)[1].strip()
            elif frontmatter_done and line.startswith('## Content'):
                # Get content (everything after ## Content header)
                content_start = i + 1
                post_text = '\n'.join(lines[content_start:]).strip()
                # Remove the approval instructions section
                if '---' in post_text:
                    post_text = post_text.split('---')[0].strip()
                break
        
        if not post_text:
            return jsonify({
                "error": "Could not parse LinkedIn draft",
                "success": False
            }), 400
        
        # Publish the post
        result = create_linkedin_post(post_text, visibility)
        
        if result.get('success'):
            # Move to Done folder
            done_dir = Path(VAULT_PATH) / "Done" / "LinkedIn_Drafts"
            done_dir.mkdir(parents=True, exist_ok=True)
            done_file = done_dir / filename
            approved_file.rename(done_file)
            
            # Log the operation
            SECURITY_CONFIG.log_action(
                action_type="linkedin_post_published",
                actor="claude_code",
                target="linkedin",
                parameters={
                    "visibility": visibility,
                    "post_id": result.get('post_id')
                },
                approval_status="human_approved",
                result="success"
            )
        
        return jsonify(result)
    
    except Exception as e:
        SECURITY_CONFIG.logger.error(f"Error publishing approved draft: {str(e)}")
        return jsonify({"error": str(e), "success": False}), 500


@app.route('/get_messages', methods=['GET'])
def get_messages():
    """
    Get recent LinkedIn messages/connection requests.
    Uses LinkedIn Messaging API (requires proper scopes).
    Falls back to empty list if messaging scope unavailable.
    """
    config = load_linkedin_config()

    if is_token_expired() or not config.get('access_token'):
        return jsonify({
            "success": False,
            "error": "Not authenticated",
            "messages": []
        }), 401

    access_token = config['access_token']

    try:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "LinkedIn-Version": "202402"
        }

        # Try to get messaging conversations
        response = requests.get(
            f"{LINKEDIN_API_BASE}/messages",
            headers=headers,
            params={"q": "participants", "count": 20},
            timeout=15
        )

        if response.status_code == 200:
            data = response.json()
            messages = []
            for element in data.get('elements', []):
                messages.append({
                    "id": element.get('id', ''),
                    "body": element.get('body', {}).get('text', ''),
                    "from": element.get('from', ''),
                    "created_at": element.get('createdAt', ''),
                })
            return jsonify({"success": True, "messages": messages})

        elif response.status_code == 403:
            # Messaging scope not available - expected for most apps
            return jsonify({
                "success": True,
                "messages": [],
                "note": "Messaging API requires additional LinkedIn Partner permissions"
            })

        else:
            return jsonify({
                "success": False,
                "error": f"LinkedIn API error: {response.status_code}",
                "messages": []
            })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "messages": []
        }), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    config = load_linkedin_config()
    return jsonify({
        'status': 'healthy',
        'service': 'linkedin-mcp',
        'timestamp': datetime.now().isoformat(),
        'authenticated': bool(config.get('access_token') and not is_token_expired())
    })


if __name__ == '__main__':
    # Load configuration on startup
    config = load_linkedin_config()
    print(f"LinkedIn MCP Server starting...")
    print(f"Client ID configured: {bool(config.get('client_id'))}")
    print(f"Access token valid: {bool(config.get('access_token') and not is_token_expired())}")
    
    # Ensure directories exist
    Path(VAULT_PATH).mkdir(parents=True, exist_ok=True)
    Path(VAULT_PATH, "Pending_Approval", "LinkedIn_Drafts").mkdir(parents=True, exist_ok=True)
    Path(VAULT_PATH, "Approved", "LinkedIn_Drafts").mkdir(parents=True, exist_ok=True)
    Path(VAULT_PATH, "Rejected", "LinkedIn_Drafts").mkdir(parents=True, exist_ok=True)
    Path(VAULT_PATH, "Done", "LinkedIn_Drafts").mkdir(parents=True, exist_ok=True)
    
    app.run(host='localhost', port=8002, debug=False)
