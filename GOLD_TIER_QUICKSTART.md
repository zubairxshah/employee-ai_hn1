# Gold Tier Quick Start Guide

**AI Personal Employee - Gold Tier**

---

## Overview

Gold Tier adds **Odoo ERP integration** for comprehensive accounting and business management. This guide gets you up and running quickly.

---

## Prerequisites

1. ✅ Silver Tier complete (all MCP servers working)
2. ✅ Python 3.8+ installed
3. ✅ Basic accounting knowledge
4. ⏳ Odoo Community Edition (install instructions below)

---

## Quick Start (5 Minutes)

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Configure Odoo Credentials

Edit `.env` file:

```bash
# Odoo ERP Credentials
ODOO_URL=http://localhost:8069
ODOO_DATABASE=odoo
ODOO_USERNAME=admin
ODOO_PASSWORD=your_password_here
```

### Step 3: Start MCP Servers

```bash
python start_mcp_servers.py
```

You should see:
```
Starting Odoo MCP server on port 8005...
[OK] Odoo MCP server started successfully
```

### Step 4: Test Odoo Connection

```bash
python test_odoo_integration.py
```

Expected output:
```
✅ Health check PASSED
✅ Authentication PASSED
✅ Get Customers PASSED
...
🎉 ALL TESTS PASSED!
```

---

## Odoo Installation (If Not Installed)

### Option 1: Download and Install (Windows)

1. Go to: https://www.odoo.com/page/download
2. Download **Odoo Community 19**
3. Run installer
4. Use default settings (port 8069)
5. Access at: http://localhost:8069

### Option 2: Quick Docker Setup

```bash
docker run -p 8069:8069 --name odoo -d odoo:19
```

Access at: http://localhost:8069
Database: `odoo`, Username: `admin`, Password: `admin`

### Option 3: Skip Odoo (Use Bank Transactions Only)

The system works without Odoo using bank transactions:
- CEO Briefing will use `Bank_Transactions.md`
- Invoice workflow requires Odoo
- Financial reporting uses local data

---

## Odoo Initial Setup (10 Minutes)

### 1. Create Database

1. Open http://localhost:8069
2. Click **"Create Database"**
3. Master password: `admin`
4. Database name: `odoo`
5. Email: `admin@example.com`
6. Password: Choose password

### 2. Install Accounting

1. Go to **Apps**
2. Search **"Invoicing"**
3. Click **Install**

### 3. Configure Company

1. Go to **Settings > Companies**
2. Edit your company
3. Set name, address, currency

### 4. Create Test Customer

1. Go to **Contacts > Create**
2. Name: `Test Customer`
3. Email: `test@example.com`
4. Save

### 5. Create Test Product

1. Go to **Invoicing > Products > Create**
2. Name: `Consulting Service`
3. Type: **Service**
4. Price: `$100`
5. Save

---

## Using Gold Tier Features

### Generate CEO Briefing

```bash
python ceo_briefing_generator.py
```

Output: `Vault/Briefings/YYYY-MM-DD_Monday_Briefing.md`

**Features:**
- Real-time revenue from Odoo
- Outstanding receivables
- Overdue invoice detection
- Payment activity
- Financial summaries

### Create Invoice (Via Agent Skill)

```python
from skills.registry import get_skill

odoo = get_skill('odoo_mcp_action')

# Create invoice
result = odoo.run(
    context={},
    parameters={
        'action': 'create_invoice',
        'partner_id': 1,  # Customer ID
        'lines': [
            {'name': 'Consulting', 'quantity': 10, 'price_unit': 150}
        ],
        'narration': 'Thank you'
    }
)

print(f"Invoice created: {result}")
```

### Create Invoice (Via MCP API)

```bash
curl -X POST http://localhost:8005/create_invoice \
  -H "Content-Type: application/json" \
  -d '{
    "partner_id": 1,
    "lines": [
      {"name": "Consulting", "quantity": 10, "price_unit": 150}
    ]
  }'
```

### Get Financial Summary

```bash
curl -X POST http://localhost:8005/get_financial_summary \
  -H "Content-Type: application/json"
```

### List Customers

```bash
curl -X POST http://localhost:8005/get_customers \
  -H "Content-Type: application/json" \
  -d '{"limit": 10}'
```

---

## Invoice Workflow

### Create Invoice Draft for Approval

```bash
python invoice_workflow.py
```

This creates an approval request in `Vault/Pending_Approval/`.

### Approve Invoice

1. Review invoice in `Vault/Pending_Approval/`
2. Move to `Vault/Approved/` to create in Odoo
3. Or move to `Vault/Rejected/` to cancel

---

## Available Endpoints

### Invoice Operations

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/create_invoice` | POST | Create invoice |
| `/get_invoices` | POST | List invoices |
| `/confirm_invoice` | POST | Confirm invoice |
| `/cancel_invoice` | POST | Cancel invoice |

### Payment Operations

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/register_payment` | POST | Register payment |
| `/get_payments` | POST | List payments |

### Customer Operations

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/get_customers` | POST | List customers |
| `/create_customer` | POST | Create customer |

### Product Operations

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/get_products` | POST | List products |
| `/create_product` | POST | Create product |

### Reporting

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/get_financial_summary` | POST | Financial summary |
| `/get_customer_statements` | POST | Customer statement |

See `ODOO_SETUP_GUIDE.md` for complete API reference.

---

## Troubleshooting

### Odoo MCP Server Won't Start

```bash
# Check if port 8005 is in use
netstat -an | grep 8005

# Check Python dependencies
pip install requests flask python-dotenv

# Run server directly for errors
python mcp_servers/odoo_mcp.py
```

### Cannot Connect to Odoo

```bash
# Check Odoo is running
curl http://localhost:8069

# Check credentials in .env
# Verify database name, username, password
```

### Authentication Failed

1. Verify Odoo credentials in `.env`
2. Check user has accounting permissions
3. Try API key instead of password

### Invoice Creation Fails

1. Check customer exists in Odoo
2. Verify chart of accounts configured
3. Check fiscal position set

---

## Configuration Reference

### .env File

```bash
# Odoo Configuration
ODOO_URL=http://localhost:8069
ODOO_DATABASE=odoo
ODOO_USERNAME=admin
ODOO_PASSWORD=your_password

# Other credentials
GMAIL_ADDRESS=your@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
```

### odoo_mcp_action.yaml

```yaml
skill_name: odoo_mcp_action
mcp:
  url: http://localhost:8005
  timeout: 60
invoice:
  default_payment_terms: 30
  auto_confirm: false
approval:
  thresholds:
    invoice_amount: 500
    payment_amount: 500
```

---

## Testing Checklist

- [ ] Odoo MCP server starts (port 8005)
- [ ] Health check passes
- [ ] Authentication works
- [ ] Can list customers
- [ ] Can create customer
- [ ] Can list products
- [ ] Can create product
- [ ] Can create invoice
- [ ] CEO briefing generates
- [ ] Financial summary shows data

Run automated tests:
```bash
python test_odoo_integration.py
```

---

## Next Steps

After Gold Tier setup:

1. ✅ Configure Odoo accounting
2. ✅ Import customers
3. ✅ Import products/services
4. ✅ Create test invoice
5. ✅ Generate first CEO briefing
6. ✅ Set up approval workflow
7. ✅ Configure notification rules

---

## Documentation

- `GOLD_TIER_COMPLETE.md` - Gold Tier completion certificate
- `ODOO_SETUP_GUIDE.md` - Detailed Odoo setup guide
- `ARCHITECTURE.md` - System architecture
- `AGENT_SKILLS.md` - Agent Skills framework
- `SCHEDULING_GUIDE.md` - Task scheduling

---

## Support

### Common Issues

**Q: Do I need Odoo for Gold Tier?**

A: Odoo is recommended but optional. Without Odoo:
- CEO Briefing uses `Bank_Transactions.md`
- Invoice workflow unavailable
- Financial reporting uses local data

**Q: Can I use Odoo Online (SaaS)?**

A: Yes, but requires:
- Odoo Online subscription
- API access enabled
- Update `ODOO_URL` to your instance

**Q: What Odoo version is supported?**

A: Odoo 18+ recommended. Odoo 17 may work with minor adjustments.

---

## Security Notes

1. **Never commit `.env`** - Contains credentials
2. **Use API keys** - Not passwords in production
3. **Enable HTTPS** - For remote Odoo access
4. **Limit permissions** - Minimum required access
5. **Regular backups** - Daily Odoo database backups

---

**Gold Tier is now ready!** 🎉

Start using your AI Employee for advanced accounting and business management.

For questions, see troubleshooting guides or Odoo documentation.
