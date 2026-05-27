# How to Post to LinkedIn - Correct Methods

**Issue:** Using `curl` with `\n` on Windows shows literal `\n` instead of line breaks

---

## ❌ WRONG Method (Don't Use)

```bash
# This shows \n literally in the post
curl -X POST http://localhost:8002/create_post -H "Content-Type: application/json" -d "{\"text\": \"Line 1\n\nLine 2\"}"
```

**Result in LinkedIn:**
```
Line 1\n\nLine 2
```

---

## ✅ CORRECT Methods

### Method 1: Use Python Script (RECOMMENDED)

```bash
python post_to_linkedin.py "Your message here"
```

Or edit `post_to_linkedin.py` with your message and run:
```bash
python post_to_linkedin.py
```

**Example:**
```bash
python post_to_linkedin.py
```

This posts the milestone message with proper formatting.

---

### Method 2: Use PowerShell (Windows)

```powershell
$body = @{
    text = @"
Line 1

Line 2
"@
    visibility = "PUBLIC"
} | ConvertTo-Json

Invoke-RestMethod -Method POST -Uri 'http://localhost:8002/create_post' -Body $body -ContentType 'application/json'
```

---

### Method 3: Use MCP Server Directly

The MCP server handles newlines correctly when called from Python code:

```python
from skills.registry import get_skill

linkedin = get_skill('linkedin_mcp_action')

result = linkedin.run(
    context={'vault_path': r'D:\prompteng\AI_Employee_Vault'},
    parameters={
        'action': 'create_post',
        'text': """Line 1

Line 2""",
        'visibility': 'PUBLIC'
    }
)
```

---

## 📝 Why This Happens

### Windows CMD vs Unix Shell

- **Unix/Linux/Mac:** `echo -e "Line1\nLine2"` interprets `\n`
- **Windows CMD:** `echo "Line1\nLine2"` shows literal `\n`
- **PowerShell:** Uses here-strings `@""@` for multi-line text

### JSON String Escaping

When you use `curl -d "{\"text\": \"Line1\nLine2\"}"`:
- CMD doesn't interpret `\n`
- LinkedIn receives literal backslash-n characters
- Result: Shows as `\n` in the post

---

## ✅ Test Results

### Fixed Post (Using Python)
- **Post ID:** `urn:li:share:7431098376697483265`
- **URL:** https://www.linkedin.com/feed/update/urn_li_share_7431098376697483265
- **Status:** ✅ Proper line breaks!

### Previous Posts (Using curl)
- Had literal `\n\n` showing in posts
- Now fixed with Python method

---

## 🚀 Quick Reference

### Post a Simple Message
```bash
python post_to_linkedin.py "Hello LinkedIn! This is a test."
```

### Post with Custom Message
Edit `post_to_linkedin.py` and change the `message` variable:

```python
message = """Your custom message here

With multiple paragraphs

#Hashtags #Here"""
```

Then run:
```bash
python post_to_linkedin.py
```

---

## 📁 Files

- `post_to_linkedin.py` - Python script for posting (RECOMMENDED)
- `scheduled_tasks/demo_linkedin_post.py` - Scheduled task example
- `scheduler.py` - Automated scheduling

---

**Status:** ✅ Use Python script for proper formatting!
