# LinkedIn MCP Server Setup Guide

**Last Updated:** February 19, 2026  
**Status:** Phase 3 - In Progress

---

## Overview

The LinkedIn MCP Server enables the AI Employee to create and publish posts on LinkedIn programmatically using the LinkedIn API v2.

### Features

- ✅ Create posts on LinkedIn (text, visibility control)
- ✅ Draft posts with human approval workflow
- ✅ OAuth 2.0 authentication
- ✅ Security: vault boundaries, input sanitization, audit logging
- ⏳ Image attachments (future enhancement)

---

## Step 1: Create LinkedIn Developer Account

### 1.1 Sign Up for LinkedIn Developer
1. Go to [LinkedIn Developer Portal](https://www.linkedin.com/developers/)
2. Sign in with your LinkedIn account
3. Accept the developer terms

### 1.2 Create a LinkedIn App
1. Click **"Create App"** in the developer portal
2. Fill in the required information:
   - **App Name:** AI Employee (or your preferred name)
   - **LinkedIn Page:** Select a company page (you must be an admin)
   - **App Logo:** Upload a logo (optional)
   - **App Description:** AI-powered employee assistant for social media posting
   - **Privacy Policy URL:** Can use a placeholder for personal use
   - **User Agreement URL:** Can use a placeholder for personal use

3. Click **"Create app"**

### 1.3 Note Your Credentials
After creating the app, you'll see:
- **Client ID** (copy this)
- **Client Secret** (click "Show" and copy this)

---

## Step 2: Configure OAuth 2.0

### 2.1 Set Redirect URL
1. In your app settings, go to **"Auth"** tab
2. Add authorized redirect URL:
   ```
   http://localhost:8002/callback
   ```
3. Save changes

> **Important:** Make sure the redirect URI matches exactly (including `http://` and port number)

### 2.2 Configure Permissions (Products)
1. Go to **"Products"** tab in your app
2. Request access to:
   - **Sign In with LinkedIn using OpenID Connect** (auto-approved)
   - **Share on LinkedIn** (w_member_social) - **May require business verification**
   - **LinkedIn Member Basic Profile** (r_liteprofile)

> **⚠️ Important Note:** The `w_member_social` permission (required for posting) often requires business verification. If your app is in "Test Mode" or pending verification:
> - Add yourself as a **Test User** in the app settings
> - Or use the permission while in development mode (works for your own account)
> - For production use, complete LinkedIn's verification process

---

## Step 3: Configure Environment Variables

### 3.1 Edit `.env` File
Add your LinkedIn credentials to the `.env` file in the project root:

```bash
# LinkedIn API Credentials
LINKEDIN_CLIENT_ID=your_client_id_here
LINKEDIN_CLIENT_SECRET=your_client_secret_here
LINKEDIN_ACCESS_TOKEN=  # Will be populated after OAuth flow
LINKEDIN_PERSON_URN=    # Will be populated after OAuth flow
```

### 3.2 Run Authentication Flow

The LinkedIn MCP server uses OAuth 2.0. Follow these steps:

```bash
# 1. Start the MCP servers
python start_mcp_servers.py

# 2. Get authorization URL
curl http://localhost:8002/get_auth_url
```

Response will include:
```json
{
  "authorization_url": "https://www.linkedin.com/oauth/v2/authorization?..."
}
```

### 3.3 Authorize the App
1. **Open the authorization URL** in your browser
2. **Sign in to LinkedIn** and authorize the app
3. **You'll be redirected** to a success page at `http://localhost:8002/callback`
4. The page will **automatically exchange** the code for a token and show the result

**If automatic exchange fails**, you can manually copy the `code` parameter from the URL and run:

```bash
curl -X POST http://localhost:8002/exchange_token ^
  -H "Content-Type: application/json" ^
  -d "{\"code\": \"YOUR_AUTHORIZATION_CODE\"}"
```

### 3.4 Verify Token
After successful authorization, check that `.linkedin_token.json` was created in the project root.

---

## Step 4: Start LinkedIn MCP Server

### 4.1 Update start_mcp_servers.py
Add the LinkedIn server to the launcher (see below).

### 4.2 Start the Server
```bash
python start_mcp_servers.py
```

The LinkedIn MCP server will start on **port 8002**.

---

## API Endpoints

### Get Capabilities
```bash
curl http://localhost:8002/capabilities
```

### Get Authorization URL
```bash
curl http://localhost:8002/get_auth_url
```

### Exchange Token
```bash
curl -X POST http://localhost:8002/exchange_token \
  -H "Content-Type: application/json" \
  -d '{"code": "AUTH_CODE"}'
```

### Create Post
```bash
curl -X POST http://localhost:8002/create_post \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello LinkedIn! This is my first automated post.",
    "visibility": "PUBLIC"
  }'
```

### Create Draft (for approval)
```bash
curl -X POST http://localhost:8002/create_draft \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Draft post content here...",
    "visibility": "PUBLIC"
  }'
```

### Check Draft Status
```bash
curl -X POST http://localhost:8002/check_draft_status \
  -H "Content-Type: application/json" \
  -d '{"filename": "DRAFT_post_20260219_120000.md"}'
```

### Execute Approved Draft
```bash
curl -X POST http://localhost:8002/execute_approved_draft \
  -H "Content-Type: application/json" \
  -d '{"filename": "DRAFT_post_20260219_120000.md"}'
```

---

## Using the LinkedIn Skill

### Python Example
```python
from skills.registry import get_skill

# Get the LinkedIn skill
linkedin = get_skill('linkedin_mcp_action')

# Create a post
result = linkedin.run(
    context={'vault_path': r'D:\prompteng\AI_Employee_Vault'},
    parameters={
        'action': 'create_post',
        'text': 'Excited to share our latest business update! #growth',
        'visibility': 'PUBLIC'
    }
)
print(result)

# Create a draft for approval
draft = linkedin.run(
    context={'vault_path': r'D:\prompteng\AI_Employee_Vault'},
    parameters={
        'action': 'create_draft',
        'text': 'Draft: Big announcement coming soon...',
        'visibility': 'PUBLIC'
    }
)
print(f"Draft created: {draft['filename']}")

# Check draft status
status = linkedin.run(
    context={'vault_path': r'D:\prompteng\AI_Employee_Vault'},
    parameters={
        'action': 'check_draft',
        'filename': draft['filename']
    }
)
print(f"Status: {status['status']}")

# Execute approved draft
if status['status'] == 'approved':
    result = linkedin.run(
        context={'vault_path': r'D:\prompteng\AI_Employee_Vault'},
        parameters={
            'action': 'execute_draft',
            'filename': draft['filename']
        }
    )
    print(f"Post published: {result['post_url']}")
```

---

## Approval Workflow

1. **Create Draft:** AI creates draft in `Pending_Approval/LinkedIn_Drafts/`
2. **Human Review:** Review the draft content
3. **Approve:** Move file to `Approved/LinkedIn_Drafts/`
4. **Publish:** AI executes the approved draft and moves to `Done/LinkedIn_Drafts/`

---

## Troubleshooting

### OAuth Authorization Errors

#### "Redirect URI Mismatch" (Most Common)
This error means the redirect URI in your LinkedIn app settings doesn't exactly match what the server is using.

**Step 1: Check your .env file**
- Verify `LINKEDIN_REDIRECT_URI=http://localhost:8002/callback` exists in `.env`
- No spaces, no quotes, no trailing slash

**Step 2: Check LinkedIn App Settings**
- Go to https://www.linkedin.com/developers/apps
- Select your app
- Click **"Auth"** tab
- Under **"Authorized redirect URLs"**, verify it's exactly:
  ```
  http://localhost:8002/callback
  ```
- Must have:
  - ✓ `http://` (not `https://`)
  - ✓ `localhost` (not `127.0.0.1`)
  - ✓ `:8002` port
  - ✓ `/callback` path
  - ✗ NO trailing slash (`/` at the end)
  - ✗ NO query parameters

**Step 3: Debug the exact URL being sent**
```bash
# Check what redirect URI the server is using
curl http://localhost:8002/debug_redirect_uri
```

This will show:
- Raw redirect URI from config
- URL-encoded version being sent to LinkedIn
- Full authorization URL

**Step 4: Fix mismatch**
If the redirect URIs don't match:
1. In LinkedIn app settings, remove the existing redirect URI
2. Save changes
3. Add it again: `http://localhost:8002/callback`
4. Save again
5. Wait 2-3 minutes for propagation
6. Restart MCP servers: `python start_mcp_servers.py`

#### "Unauthorized - Access Denied" or "App Not Approved"
- Your LinkedIn app may be in **Test Mode**
- Go to app settings → **Test Users** section
- Add your LinkedIn account as a test user
- Or complete LinkedIn's business verification process

#### "w_member_social Permission Required"
- This permission requires business verification for production use
- For development/personal use:
  - Keep your app in development mode
  - Add yourself as a test user
  - The permission works for your own profile without full verification

#### "Callback Page Shows Error"
- Check the error message on the callback page
- Common issues:
  - **Invalid client_id**: Verify `LINKEDIN_CLIENT_ID` in `.env`
  - **Invalid redirect_uri**: Must match exactly in LinkedIn app settings
  - **Expired code**: Authorization codes expire quickly; use immediately

### "Client ID not configured"
- Check `.env` file has `LINKEDIN_CLIENT_ID`
- Restart the MCP server after editing `.env`

### "Token expired"
- LinkedIn tokens expire after 60 days
- Re-run the OAuth flow to get a new token

### "Permission denied"
- Ensure your app has the `w_member_social` permission
- Check that you're using the correct Person URN

### "Post failed with 400 error"
- Check text length (max 3000 characters)
- Verify visibility is `PUBLIC` or `CONNECTIONS_ONLY`

### Manual Token Exchange
If the automatic token exchange fails:
```bash
# Copy the code from the callback URL
curl -X POST http://localhost:8002/exchange_token ^
  -H "Content-Type: application/json" ^
  -d "{\"code\": \"YOUR_CODE_HERE\"}"
```

### Quick Debug Commands

```bash
# Check server status
curl http://localhost:8002/capabilities

# Get authorization URL
curl http://localhost:8002/get_auth_url

# Debug redirect URI configuration
curl http://localhost:8002/debug_redirect_uri

# Restart MCP servers
python start_mcp_servers.py
```

---

## Security Considerations

### Vault Boundaries
- All draft files stored within vault
- Prevents unauthorized file system access

### Input Sanitization
- All post text is sanitized before API calls
- Prevents injection attacks

### Audit Logging
- All post operations are logged
- Includes actor, target, parameters, and result

### Human Approval
- Sensitive posts can require approval
- Draft workflow ensures oversight

---

## Next Steps

### Image Support (Future)
- Implement media upload API
- Add `images` parameter to create_post
- Support for multiple images

### Scheduling (Future)
- Add scheduled posting capability
- Integration with Task Scheduler

### Analytics (Future)
- Fetch post engagement metrics
- Generate performance reports

---

## File Locations

| File | Purpose |
|------|---------|
| `mcp_servers/linkedin_mcp.py` | LinkedIn MCP server |
| `skills/action/linkedin_mcp_action.py` | LinkedIn action skill |
| `skills/config/linkedin_mcp_action.yaml` | Skill configuration |
| `.linkedin_token.json` | OAuth token (auto-created) |
| `Vault/Pending_Approval/LinkedIn_Drafts/` | Draft posts |
| `Vault/Approved/LinkedIn_Drafts/` | Approved drafts |
| `Vault/Done/LinkedIn_Drafts/` | Published posts |

---

**Ready to proceed with LinkedIn integration!**
