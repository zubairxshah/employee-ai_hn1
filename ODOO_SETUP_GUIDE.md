# Odoo ERP Setup Guide

**For AI Personal Employee - Gold Tier Integration**

---

## Overview

This guide walks you through setting up Odoo Community Edition for integration with the AI Personal Employee system. Odoo provides comprehensive accounting, invoicing, and financial management capabilities.

---

## Table of Contents

1. [Odoo Installation Options](#odoo-installation-options)
2. [Local Installation (Development)](#local-installation-development)
3. [Cloud Installation (Production)](#cloud-installation-production)
4. [Initial Configuration](#initial-configuration)
5. [Accounting Setup](#accounting-setup)
6. [API Integration](#api-integration)
7. [Testing Connection](#testing-connection)
8. [Troubleshooting](#troubleshooting)

---

## Odoo Installation Options

### Option 1: Local Installation (Recommended for Development)

**Pros:**
- Free (Community Edition)
- Full control
- No internet dependency
- Fast development

**Cons:**
- Requires local resources
- Manual backups
- Not accessible remotely

### Option 2: Odoo.sh (Odoo's Hosting)

**Pros:**
- Managed hosting
- Automatic backups
- Easy scaling
- Built-in CI/CD

**Cons:**
- Paid service (~$25/month)
- Less control

### Option 3: Cloud VM (AWS/Azure/GCP/Oracle)

**Pros:**
- Full control
- 24/7 accessibility
- Scalable
- Can use free tiers

**Cons:**
- Requires server management
- Setup complexity

---

## Local Installation (Development)

### Step 1: Download Odoo

1. Go to: https://www.odoo.com/page/download
2. Download **Odoo Community 19** (latest LTS version)
3. Choose your platform (Windows/Linux/macOS)

### Step 2: Install Odoo (Windows)

```bash
# Run the installer
# Follow the installation wizard
# Default installation path: C:\Program Files\Odoo 19
```

**Installation Options:**
- PostgreSQL: Include in installation
- Port: Use default (8069)
- Service: Install as Windows service

### Step 3: Install Odoo (Linux - Ubuntu/Debian)

```bash
# Add Odoo repository
wget -O - https://nightly.odoo.com/ODOO.key | apt-key add -
echo "deb http://nightly.odoo.com/19.0/nightly/deb/ ./" >> /etc/apt/sources.list.d/odoo.list

# Update and install
apt-get update
apt-get install odoo

# Start Odoo
systemctl start odoo
systemctl enable odoo
```

### Step 4: Access Odoo

Open browser and navigate to:
```
http://localhost:8069
```

### Step 5: Create Database

1. Click **"Create Database"**
2. Enter master password (default: `admin`)
3. Database name: `odoo` (or your choice)
4. Email: `admin@example.com`
5. Password: Choose a strong password
6. Click **"Create Database"**

---

## Cloud Installation (Production)

### Option 1: Odoo.sh

1. Go to: https://www.odoo.sh
2. Sign up for account
3. Create new project
4. Deploy Odoo 19 Community
5. Configure domain and SSL

### Option 2: Oracle Cloud Free Tier

```bash
# Create VM instance (Free Tier)
# Shape: VM.Standard.E2.1.Micro
# OS: Ubuntu 22.04

# Install Odoo
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo apt install odoo

# Configure Odoo
sudo nano /etc/odoo/odoo.conf

# Set external IP and domain
[options]
admin_passwd = your_master_password
db_host = localhost
db_port = 5432
db_user = odoo
db_password = odoo
http_port = 8069

# Restart Odoo
sudo systemctl restart odoo
```

### Option 3: AWS EC2

```bash
# Launch EC2 instance
# AMI: Ubuntu 22.04
# Instance: t2.micro (Free Tier eligible)

# Security Group Rules:
# - SSH (22) - Your IP
# - HTTP (8069) - Your IP (or 0.0.0.0/0 with HTTPS)

# Install Odoo (same as Linux above)
```

---

## Initial Configuration

### Step 1: Install Accounting Module

1. Log in to Odoo
2. Go to **Apps**
3. Search for **"Accounting"**
4. Click **"Install"** on **"Invoicing"** (free) or **"Accounting"** (full)

### Step 2: Configure Company

1. Go to **Settings > Users & Companies > Companies**
2. Edit your company
3. Set:
   - Company name
   - Address
   - Tax ID
   - Currency
   - Fiscal year

### Step 3: Configure Chart of Accounts

1. Go to **Accounting > Configuration > Chart of Accounts**
2. Odoo auto-generates based on country
3. Review and customize as needed

### Step 4: Set Up Journals

1. Go to **Accounting > Configuration > Journals**
2. Default journals created:
   - Sales (Customer Invoices)
   - Purchases (Vendor Bills)
   - Bank
   - Cash
3. Configure bank accounts

### Step 5: Configure Payment Terms

1. Go to **Accounting > Configuration > Payment Terms**
2. Common terms:
   - Immediate payment
   - 30 days end of month
   - 50% advance, 50% on delivery
3. Create custom terms as needed

---

## Accounting Setup

### Create Customer

1. Go to **Contacts > Create**
2. Enter customer details:
   - Name
   - Email
   - Phone
   - Address
   - Tax ID (for B2B)
3. Mark as **Customer**
4. Save

### Create Product/Service

1. Go to **Invoicing > Products > Products**
2. Click **Create**
3. Enter:
   - Product name
   - Type: Service or Product
   - Sales price
   - Tax
4. Save

### Create Invoice

1. Go to **Invoicing > Customers > Invoices**
2. Click **Create**
3. Select customer
4. Add invoice lines:
   - Product/Service
   - Quantity
   - Price
5. Set invoice date
6. Set payment due date
7. Click **"Confirm"** to post

### Register Payment

1. Open posted invoice
2. Click **"Register Payment"**
3. Enter:
   - Amount
   - Payment date
   - Payment method
4. Click **"Create Payment"**

---

## API Integration

### Enable API Access

Odoo provides JSON-RPC API by default. No additional configuration needed.

### Get API Key (Recommended)

1. Go to **Settings > Users & Companies > Users**
2. Edit your user
3. Under **Preferences**, click **"Action"** > **"Reset Access Rights"**
4. Copy the API key shown

### Authentication Methods

**Method 1: Session Authentication**
```python
import requests

# Authenticate
payload = {
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
        "db": "odoo",
        "login": "admin",
        "password": "your_password"
    },
    "id": 1
}

response = requests.post(
    "http://localhost:8069/web/session/authenticate",
    json=payload
)
```

**Method 2: API Key Authentication**
```python
# Use API key instead of password
payload = {
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
        "db": "odoo",
        "login": "admin",
        "key": "your_api_key"
    },
    "id": 1
}
```

---

## Testing Connection

### Test with cURL

```bash
# Health check (Odoo MCP)
curl http://localhost:8005/health

# Authenticate
curl -X POST http://localhost:8005/authenticate

# Get customers
curl -X POST http://localhost:8005/get_customers \
  -H "Content-Type: application/json" \
  -d '{"limit": 5}'

# Get invoices
curl -X POST http://localhost:8005/get_invoices \
  -H "Content-Type: application/json" \
  -d '{"state": "posted", "limit": 10}'
```

### Test with Python

```python
import requests

# Test Odoo MCP connection
response = requests.get('http://localhost:8005/health')
print(f"Health: {response.json()}")

# Test get customers
response = requests.post(
    'http://localhost:8005/get_customers',
    json={'limit': 5}
)
print(f"Customers: {response.json()}")
```

### Test with AI Employee

```bash
# Start MCP servers
python start_mcp_servers.py

# Run Odoo test
python test_odoo_connection.py
```

---

## Troubleshooting

### Issue: Cannot Connect to Odoo

**Solution:**
```bash
# Check if Odoo is running
# Windows: Check Services
# Linux: systemctl status odoo

# Check port
netstat -an | grep 8069

# Check firewall
# Windows: Allow port 8069
# Linux: sudo ufw allow 8069
```

### Issue: Authentication Failed

**Solution:**
1. Verify database name
2. Verify username/password
3. Check user has API access
4. Try resetting password

### Issue: Permission Denied

**Solution:**
1. Check user has accounting permissions
2. Go to **Settings > Users**
3. Edit user
4. Grant **Invoicing / User** or **Invoicing / Manager** access

### Issue: MCP Server Not Starting

**Solution:**
```bash
# Check Python dependencies
pip install requests flask python-dotenv

# Check port availability
netstat -an | grep 8005

# Check logs
python mcp_servers/odoo_mcp.py
# Look for error messages
```

### Issue: Invoice Creation Fails

**Solution:**
1. Check customer exists
2. Check products/services configured
3. Check chart of accounts configured
4. Check fiscal position set
5. Review Odoo logs

---

## Configuration Reference

### .env File

```bash
# Odoo ERP Credentials
ODOO_URL=http://localhost:8069
ODOO_DATABASE=odoo
ODOO_USERNAME=admin
ODOO_PASSWORD=your_password_or_api_key
```

### odoo_mcp_action.yaml

```yaml
skill_name: odoo_mcp_action
version: 1.0.0
mcp:
  url: http://localhost:8005
  timeout: 60
  retry_attempts: 3
invoice:
  default_payment_terms: 30
  auto_confirm: false
approval:
  required_for:
    - create_invoice
    - register_payment
  thresholds:
    invoice_amount: 500
    payment_amount: 500
```

---

## Security Best Practices

1. **Use API Keys** - Never use passwords in production
2. **Enable HTTPS** - Always use HTTPS for remote access
3. **Limit Permissions** - Grant minimum required access
4. **Regular Backups** - Schedule daily database backups
5. **Monitor Access** - Review access logs regularly
6. **Update Regularly** - Keep Odoo updated with security patches

---

## Next Steps

After completing Odoo setup:

1. ✅ Test MCP server connection
2. ✅ Create test customer
3. ✅ Create test product/service
4. ✅ Create test invoice
5. ✅ Register test payment
6. ✅ Generate CEO briefing
7. ✅ Review financial summary

---

## Additional Resources

- **Odoo Documentation:** https://www.odoo.com/documentation
- **Odoo Community:** https://www.odoo.com/forum/help-1
- **Odoo GitHub:** https://github.com/odoo/odoo
- **JSON-RPC API:** https://www.odoo.com/documentation/developer/reference/backend/orm.html

---

**Setup Complete!** 🎉

Your Odoo ERP is now ready for integration with AI Personal Employee.
