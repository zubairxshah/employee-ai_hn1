# Odoo Setup via Docker

Quick guide to install and configure Odoo for the AI Personal Employee system.

---

## Prerequisites

- Docker and Docker Compose installed
- Ports 8069 (Odoo) and 5432 (PostgreSQL) available

---

## Step 1: Start Odoo with Docker Compose

Create a `docker-compose.yml` (or use the one in `deploy/docker-compose.cloud.yml`):

```yaml
version: "3.8"
services:
  postgres:
    image: postgres:15
    container_name: odoo-postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: odoo
      POSTGRES_USER: odoo
      POSTGRES_PASSWORD: your_secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  odoo:
    image: odoo:17
    container_name: odoo-app
    restart: unless-stopped
    depends_on:
      - postgres
    environment:
      HOST: postgres
      USER: odoo
      PASSWORD: your_secure_password
    ports:
      - "8069:8069"
    volumes:
      - odoo_data:/var/lib/odoo
      - odoo_addons:/mnt/extra-addons

volumes:
  postgres_data:
  odoo_data:
  odoo_addons:
```

```bash
docker-compose up -d
```

Wait 30 seconds for Odoo to initialize, then open http://localhost:8069.

---

## Step 2: Create the Database

1. Open http://localhost:8069 in your browser
2. You'll see the database creation screen
3. Fill in:
   - **Master Password**: choose something secure (this protects database management)
   - **Database Name**: `odoo`
   - **Email**: `admin@yourcompany.com`
   - **Password**: choose your admin password
   - **Language**: English
   - **Country**: your country
4. Click **Create Database**
5. Wait for setup to complete (1-2 minutes)

---

## Step 3: Install Required Modules

1. Log in with the email/password you just created
2. Go to **Apps** from the top menu
3. Search and install these modules:
   - **Invoicing** (free accounting module)
   - **Sales** (customer management)
   - **Contacts** (address book)
4. Click **Install** on each one and wait for it to complete

---

## Step 4: Configure Your Company

1. Go to **Settings** > **General Settings**
2. Under **Companies**, click your company name
3. Fill in:
   - Company Name
   - Address
   - Currency
   - Tax ID (if applicable)
4. Save

---

## Step 5: Set Up for AI Employee Integration

### Create a Test Customer

1. Go to **Contacts** > **Create**
2. Enter: Name, Email, Phone
3. Save

### Create a Test Product/Service

1. Go to **Invoicing** > **Products** > **Create**
2. Enter:
   - Name: e.g., "Consulting Services"
   - Type: **Service**
   - Sales Price: e.g., 150.00
3. Save

### Create a Test Invoice

1. Go to **Invoicing** > **Customers** > **Invoices** > **Create**
2. Select a customer
3. Add an invoice line (product, quantity, price)
4. Click **Confirm** to post the invoice

---

## Step 6: Configure .env for the AI Employee

Add these to your `.env` file (in the `employee/` project root):

```env
ODOO_URL=http://localhost:8069
ODOO_DATABASE=odoo
ODOO_USERNAME=admin
ODOO_PASSWORD=your_admin_password_here
```

Replace `your_admin_password_here` with the password you set in Step 2.

---

## Step 7: Generate an API Key (Optional, Recommended)

Using an API key is more secure than using your password:

1. Log in to Odoo
2. Click your user avatar (top right) > **My Profile**
3. Go to **Account Security** tab
4. Under **API Keys**, click **New API Key**
5. Name it: `ai-employee`
6. Copy the key and add it to `.env`:

```env
ODOO_PASSWORD=your_api_key_here
```

The MCP server uses this as the password for JSON-RPC authentication.

---

## Step 8: Verify the Connection

```bash
# Start the Odoo MCP server
cd D:\prompteng\employee
python mcp_servers/odoo_mcp.py

# In another terminal, test the health endpoint
curl http://localhost:8005/health

# Test getting customers
curl -X POST http://localhost:8005/get_customers -H "Content-Type: application/json" -d "{\"limit\": 5}"
```

Expected health response:

```json
{
  "status": "healthy",
  "service": "odoo_mcp",
  "timestamp": "2026-03-03T20:00:00"
}
```

---

## Docker Management

### Start / Stop / Restart

```bash
# Start
docker-compose up -d

# Stop (keeps data)
docker-compose down

# Restart
docker-compose restart

# View logs
docker-compose logs -f odoo
```

### Backup the Database

```bash
# Manual backup
docker exec odoo-postgres pg_dump -U odoo odoo | gzip > odoo_backup_$(date +%Y%m%d).sql.gz

# Restore from backup
gunzip -c odoo_backup_20260303.sql.gz | docker exec -i odoo-postgres psql -U odoo odoo
```

### Reset Everything (Destroys All Data)

```bash
docker-compose down -v
docker-compose up -d
```

---

## Cloud Deployment

For deploying Odoo on a cloud VM (Oracle Free Tier), see [CLOUD_VM_DEPLOYMENT.md](CLOUD_VM_DEPLOYMENT.md).

The cloud deployment uses `deploy/docker-compose.cloud.yml` which includes:
- Odoo + PostgreSQL
- Cloud Agent (draft-only mode)
- Nginx reverse proxy
- Automated backups

---

## Troubleshooting

### Cannot access http://localhost:8069

- Check containers are running: `docker ps`
- Check logs: `docker-compose logs odoo`
- Wait longer on first startup (database initialization takes time)

### Authentication failed

- Verify database name matches `ODOO_DATABASE` in `.env`
- Verify password/API key is correct
- Try logging in via the web UI first to confirm credentials work

### Invoice creation fails

- Make sure Invoicing module is installed
- Make sure at least one customer exists
- Make sure at least one product/service exists
- Check Odoo logs: `docker-compose logs odoo`

### MCP server won't connect to Odoo

- Check Odoo is running: `curl http://localhost:8069/web/health`
- Check `ODOO_URL` in `.env` matches where Odoo is running
- For cloud Docker setup, use `http://odoo:8069` (container name) instead of localhost

---

## Quick Reference

| What | Where |
|------|-------|
| Odoo Web UI | http://localhost:8069 |
| Odoo MCP Server | http://localhost:8005 |
| PostgreSQL | localhost:5432 |
| Database name | `odoo` |
| Default user | `admin` |
| Docker data | `postgres_data`, `odoo_data` volumes |
| MCP Server file | `mcp_servers/odoo_mcp.py` |
| Action Skill file | `skills/action/odoo_mcp_action.py` |
