# LinkedIn Lead Generation - Testing Guide

## 🎯 Quick Start

### Run Interactive Test
```bash
cd D:\prompteng\employee
python test_real_linkedin_lead.py
```

---

## 📍 Where to Check Results

### 1. Lead Records (Complete Details)
```
Location: D:\prompteng\AI_Employee_Vault\Leads\
Files: LEAD_*.json
```

**What you'll find:**
- Customer ID
- Lead score (0-100)
- Keywords detected
- Interests identified
- LinkedIn profile URL
- Original message content
- Status (new, contacted, qualified, converted, lost)

**Example:**
```json
{
  "customer_id": 60,
  "lead_data": {
    "name": "Ahmed Khan",
    "company": "Global Tech Solutions",
    "email": "ahmed.khan@globaltechsolutions.com",
    "lead_score": 90,
    "keywords": ["interested", "looking for", "solution"],
    "linkedin_url": "https://www.linkedin.com/in/ahmedkhan"
  },
  "status": "new"
}
```

---

### 2. Odoo Customers (CRM)
```
URL: http://localhost:8069
Login: admin / admin
Navigate: Sales → Customers
```

**What you'll find:**
- Customer name
- Email address
- Phone number
- Company (in Street field)
- LinkedIn URL (in VAT field)
- Create date

**Search for your lead:**
- Search by name or email
- Look for LinkedIn URL in VAT field

---

### 3. Gmail Sent Folder (Follow-up Emails)
```
URL: https://mail.google.com
Account: emaxis.newsletter@gmail.com
Folder: Sent
```

**What you'll find:**
- Follow-up emails sent to leads with score ≥ 50
- Subject: "Great connecting with you on LinkedIn, [Name]!"
- Personalized message based on lead's interests

---

### 4. Processed Messages
```
Location: D:\prompteng\AI_Employee_Vault\Processed_LinkedIn\
Files: LINKEDIN_*.json
```

**What you'll find:**
- Original message data
- Processing timestamp
- Message ID tracking

---

## 🧪 Testing Methods

### Method 1: Interactive Test (Recommended)
```bash
python test_real_linkedin_lead.py
```
**Steps:**
1. Run the script
2. Copy-paste real LinkedIn message data when prompted
3. Watch the processing happen in real-time
4. Check the 3 locations above

---

### Method 2: Pre-defined Test Data
```bash
python linkedin_to_customer_workflow.py
```
Uses sample data for quick testing.

---

### Method 3: Full Test Suite
```bash
python test_linkedin_to_customer.py
```
Runs 4 test scenarios + lead scoring validation.

---

## 📊 Lead Scoring Reference

| Score Range | Classification | Action |
|-------------|---------------|--------|
| 80-100 | 🔥 HOT | Immediate follow-up, high priority |
| 50-79 | 🟡 WARM | Send follow-up email, nurture |
| 20-49 | ❄️ COLD | No auto follow-up, keep in CRM |

### Keywords That Increase Score

**+20 points (High Intent):**
- interested, want, need, looking for
- require, budget, pricing, quote, proposal

**+10 points (Medium Intent):**
- learn more, discuss, meeting, call
- chat, explore, opportunity

**+5 points (Business Terms):**
- business, company, service, product
- solution, project, contract

---

## 🔍 Real Test Example

### Step 1: Get LinkedIn Data
Go to: https://www.linkedin.com/messaging/

Copy this info:
```
Sender Name: John Smith
Headline: CEO at TechCorp
Message: Hi! I'm interested in your services...
Profile URL: https://linkedin.com/in/johnsmith
```

### Step 2: Run Test
```bash
python test_real_linkedin_lead.py
```

Paste the data when prompted.

### Step 3: Verify Results

**Check Odoo:**
```
1. Open http://localhost:8069
2. Login: admin / admin
3. Go to: Sales → Customers
4. Search: "John Smith"
5. Verify: Email, Company, LinkedIn URL present
```

**Check Gmail:**
```
1. Open https://mail.google.com
2. Go to: Sent folder
3. Look for: "Great connecting with you on LinkedIn, John Smith!"
4. Verify: Email sent to John's email address
```

**Check Lead File:**
```
1. Open: D:\prompteng\AI_Employee_Vault\Leads\
2. Find: LEAD_*_*.json (most recent)
3. Open with: Notepad or VS Code
4. Verify: All data captured correctly
```

---

## ⚠️ Troubleshooting

### Issue: Lead not created in Odoo
**Check:**
```bash
# Verify Odoo MCP is running
curl http://localhost:8005/health
```

### Issue: Follow-up email not sent
**Check:**
1. Lead score must be ≥ 50
2. Email must be present in message
3. Email MCP must be running:
```bash
curl http://localhost:8001/send_email -d '{"to":"test@test.com","subject":"test","body":"test"}'
```

### Issue: Lead score too low/high
**Check:**
- Review keywords in message
- Check headline for company info
- Adjust scoring thresholds in code

---

## 📈 Lead Status Workflow

```
new → contacted → qualified → converted
                  ↓
                lost
```

**Update status manually:**
1. Open lead JSON file
2. Change `"status": "new"` to desired status
3. Add notes: `"notes": ["Called on 2026-03-01"]`

---

## 🚀 Quick Commands

```bash
# Test with real data
python test_real_linkedin_lead.py

# Run full test suite
python test_linkedin_to_customer.py

# Check Odoo customers
curl http://localhost:8005/get_customers -d "{\"limit\": 10}"

# View lead files
dir D:\prompteng\AI_Employee_Vault\Leads

# Check all services
curl http://localhost:8005/health  # Odoo
curl http://localhost:8001/health  # Email (if available)
```

---

## ✅ Test Checklist

Before testing, ensure:
- [ ] Odoo MCP server running (port 8005)
- [ ] Email MCP server running (port 8001)
- [ ] Odoo database accessible (http://localhost:8069)
- [ ] Gmail credentials configured (.env file)

After testing, verify:
- [ ] Customer created in Odoo
- [ ] Lead file created in Leads folder
- [ ] Follow-up email in Gmail Sent (if score ≥ 50)
- [ ] Message moved to Processed_LinkedIn folder

---

**Status:** ✅ Ready for Production Testing  
**Last Updated:** March 1, 2026
