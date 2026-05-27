# Gmail API Setup Guide

## Overview
This guide walks you through setting up Gmail API access for the AI Employee Gmail Watcher.

## Prerequisites
- Google Account (Gmail)
- Internet connection

## Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Name it: `AI Employee` (or your preferred name)
4. Click "Create"

## Step 2: Enable Gmail API

1. In your project, go to **APIs & Services** → **Library**
2. Search for "Gmail API"
3. Click on "Gmail API"
4. Click **Enable**

## Step 3: Configure OAuth Consent Screen

1. Go to **APIs & Services** → **OAuth consent screen**
2. Select **External** (unless you have Google Workspace)
3. Click **Create**

### Fill in the form:
- **App name**: AI Employee
- **User support email**: Your email address
- **App logo**: (optional)
- **App domain**: Leave blank for local testing
- **Developer contact**: Your email address

4. Click **Save and Continue**

### Scopes:
1. Click **Add or Remove Scopes**
2. Add these scopes:
   - `https://www.googleapis.com/auth/gmail.readonly` (Read emails)
   - `https://www.googleapis.com/auth/gmail.send` (Send emails)
3. Click **Update**
4. Click **Save and Continue**

### Test users:
1. Click **Add Users**
2. Add your Gmail address
3. Click **Save and Continue**

## Step 4: Create OAuth2 Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth client ID**
3. Application type: **Desktop app**
4. Name: `AI Employee Desktop Client`
5. Click **Create**

### Download Credentials:
1. A popup will show your Client ID and Secret
2. Click **Download JSON**
3. Save the file as `gmail_credentials.json`
4. Place it in: `D:\prompteng\employee\`

**⚠️ IMPORTANT:** Never commit this file to version control!

## Step 5: Generate Refresh Token

Run the authentication script to generate your refresh token:

```bash
python scripts/gmail_auth.py
```

This will:
1. Open a browser window
2. Ask you to sign in to Google
3. Ask for permission to access Gmail
4. Save the credentials locally

## Step 6: Verify Setup

Test the Gmail Watcher:

```bash
python -c "from skills.perception.gmail_watcher import GmailWatcherSkill; print('Gmail skill loaded!')"
```

## File Locations

After setup, you should have:
```
D:\prompteng\employee\
├── gmail_credentials.json    # OAuth2 credentials (DO NOT COMMIT)
└── .env                       # Contains GMAIL_CLIENT_ID, etc.
```

## Environment Variables

Add to your `.env` file:
```env
# Gmail API Credentials
GMAIL_CLIENT_ID=your_client_id_from_json
GMAIL_CLIENT_SECRET=your_client_secret_from_json
GMAIL_REFRESH_TOKEN=generated_by_auth_script
```

## Troubleshooting

### Error: "Access blocked: This app's request is invalid"
- Make sure you added your email as a test user
- Verify OAuth consent screen is configured

### Error: "Credentials expired"
- Re-run the auth script to refresh tokens
- Check token expiration in Google Cloud Console

### Error: "Gmail API not enabled"
- Go to Google Cloud Console → APIs & Services → Library
- Enable Gmail API

## Security Notes

1. **Never share** your `gmail_credentials.json`
2. **Never commit** credentials to git
3. Use **test user** mode for development
4. Review **permissions** in Google Account settings regularly

## Next Steps

After setup:
1. Configure `skills/config/gmail_watcher.yaml` with your credentials path
2. Run `python test_skills.py` to verify Gmail skill works
3. Start using Gmail Watcher in production

## References

- [Gmail API Documentation](https://developers.google.com/gmail/api)
- [OAuth2 for Desktop Apps](https://developers.google.com/identity/protocols/oauth2/native-app)
- [Google Cloud Console](https://console.cloud.google.com/)
