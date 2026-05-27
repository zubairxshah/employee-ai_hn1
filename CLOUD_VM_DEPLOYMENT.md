# Cloud VM Deployment Guide

Deploy the AI Personal Employee cloud agent on Oracle Cloud Free Tier (or any Linux VM).

---

## Requirements

### VM Minimum Specs

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 1 vCPU (ARM or x86) | 2 vCPU |
| RAM | 2 GB | 4 GB |
| Disk | 20 GB | 50 GB |
| OS | Ubuntu 22.04+ | Ubuntu 24.04 LTS |
| Network | Public IP + ports 80, 443 | Static IP |

Oracle Cloud Free Tier provides **VM.Standard.A1.Flex** (ARM, up to 4 vCPU / 24 GB RAM) or **VM.Standard.E2.1.Micro** (x86, 1 vCPU / 1 GB RAM). The ARM instance is recommended.

### Software Requirements

| Software | Version | Purpose |
|----------|---------|---------|
| Docker | 24+ | Container runtime |
| Docker Compose | 2.20+ | Multi-container orchestration |
| Git | 2.30+ | Vault sync |
| Python | 3.11+ | Cloud agent (inside container) |

### Network Ports

| Port | Service | Access |
|------|---------|--------|
| 22 | SSH | Your IP only |
| 80 | Nginx (HTTP) | Public (redirects to HTTPS) |
| 443 | Nginx (HTTPS) | Public |
| 8069 | Odoo (internal) | Docker network only |
| 9000 | Health endpoint | Docker network / monitoring |

### Credentials Needed (Cloud-Safe Only)

The cloud agent uses **read-only / draft-only** credentials. Never deploy these on cloud:

| Credential | Cloud | Local |
|------------|-------|-------|
| Gmail Client ID/Secret/Refresh Token | Yes (read-only) | Yes |
| Gmail App Password (SMTP send) | **NO** | Yes |
| LinkedIn Client ID/Secret | Yes | Yes |
| Facebook App ID/Secret | Yes | Yes |
| Twitter OAuth keys | Yes | Yes |
| Odoo URL/Username/Password | Yes | Yes |
| WhatsApp phone/session | **NO** | Yes |
| Bank API token | **NO** | Yes |

---

## Step 1: Create the VM

### Oracle Cloud

1. Sign up at https://cloud.oracle.com (free tier, no credit card for always-free)
2. Go to **Compute > Instances > Create Instance**
3. Choose:
   - Shape: **VM.Standard.A1.Flex** (ARM) - 2 vCPU, 4 GB RAM
   - Image: **Ubuntu 22.04** (Canonical)
   - Boot volume: **50 GB**
4. Add your SSH public key
5. Create and note the **Public IP**

### Firewall Rules (Security List)

Add ingress rules:

```
TCP 22   (SSH)       - Source: your IP
TCP 80   (HTTP)      - Source: 0.0.0.0/0
TCP 443  (HTTPS)     - Source: 0.0.0.0/0
```

### Also open ports on the VM itself:

```bash
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save
```

---

## Step 2: Install Docker

SSH into the VM:

```bash
ssh -i ~/.ssh/your_key ubuntu@YOUR_PUBLIC_IP
```

Run the bootstrap script (or do it manually):

```bash
# Option A: Use the provided setup script
git clone https://github.com/your-user/ai-employee.git ~/ai-employee
chmod +x ~/ai-employee/deploy/setup_cloud.sh
~/ai-employee/deploy/setup_cloud.sh
```

```bash
# Option B: Manual install
sudo apt update && sudo apt upgrade -y

# Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
    -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Git
sudo apt install -y git

# Log out and back in for docker group
exit
```

---

## Step 3: Clone and Configure

```bash
ssh -i ~/.ssh/your_key ubuntu@YOUR_PUBLIC_IP

# Clone repository
git clone https://github.com/your-user/ai-employee.git ~/ai-employee
cd ~/ai-employee/deploy

# Create cloud environment file
cp cloud.env.example cloud.env
nano cloud.env
```

Edit `cloud.env` with your actual credentials. Remember:
- Set a strong `POSTGRES_PASSWORD`
- Set `ODOO_PASSWORD` to match what you'll use in Odoo
- Add your Gmail read-only credentials (Client ID, Secret, Refresh Token)
- Add your social media API keys
- **Do NOT add** `GMAIL_APP_PASSWORD`, `WHATSAPP_*`, or `BANK_API_TOKEN`

---

## Step 4: Set Up Vault Git Sync

The vault syncs between cloud and local via a private Git repository.

```bash
# Create a private repo on GitHub (e.g., ai-employee-vault)
# Then on the VM:

# Generate SSH key for the VM
ssh-keygen -t ed25519 -C "cloud-agent" -f ~/.ssh/vault_key -N ""

# Add the public key to GitHub (Settings > SSH Keys)
cat ~/.ssh/vault_key.pub

# Configure SSH
cat >> ~/.ssh/config << 'EOF'
Host github.com
    IdentityFile ~/.ssh/vault_key
    StrictHostKeyChecking no
EOF

# Clone vault
git clone git@github.com:your-user/ai-employee-vault.git ~/ai-employee/vault

# Update cloud.env
# VAULT_REMOTE_URL=git@github.com:your-user/ai-employee-vault.git
# VAULT_SYNC_ENABLED=true
```

On your **local Windows machine**, also set up the same vault repo:

```bash
cd D:\prompteng\AI_Employee_Vault
git init
git remote add origin git@github.com:your-user/ai-employee-vault.git
git add -A
git commit -m "Initial vault sync"
git push -u origin main
```

---

## Step 5: Deploy

```bash
cd ~/ai-employee/deploy

# Start all services
docker-compose -f docker-compose.cloud.yml up -d

# Check status
docker-compose -f docker-compose.cloud.yml ps

# View logs
docker-compose -f docker-compose.cloud.yml logs -f cloud_agent
```

### Verify Services

```bash
# Health check
curl http://localhost:9000/health

# Odoo web UI
curl -s http://localhost:8069/web/health

# Check all containers
docker ps
```

Expected output:

```
CONTAINER ID  IMAGE          STATUS                    PORTS
xxxx          employee_cloud  Up (healthy)             0.0.0.0:9000->9000/tcp
xxxx          odoo:17        Up (healthy)             0.0.0.0:8069->8069/tcp
xxxx          postgres:15    Up (healthy)             5432/tcp
xxxx          nginx:alpine   Up                       0.0.0.0:80->80/tcp, 443/tcp
```

---

## Step 6: Configure Odoo (First Time)

1. Open `http://YOUR_PUBLIC_IP` in your browser
2. Create the database:
   - Master Password: set something secure
   - Database Name: `odoo`
   - Email: `admin@yourdomain.com`
   - Password: must match `ODOO_PASSWORD` in `cloud.env`
3. Install modules: **Invoicing**, **Sales**, **Contacts**
4. Configure your company details

See [ODOO_NEXT_STEPS.md](ODOO_NEXT_STEPS.md) for detailed Odoo setup via Docker.

---

## Step 7: Set Up HTTPS (Optional but Recommended)

```bash
# Install certbot
sudo apt install certbot

# Get certificate (replace with your domain)
sudo certbot certonly --webroot -w /var/www/certbot \
    -d your-domain.com --agree-tos -m your@email.com

# Update nginx.conf to enable HTTPS block
# Then restart nginx
docker-compose -f docker-compose.cloud.yml restart nginx
```

---

## Step 8: Set Up Automated Backups

```bash
# Make backup script executable
chmod +x ~/ai-employee/deploy/backup_odoo.sh

# Add to crontab (daily at 2 AM)
crontab -e
# Add this line:
0 2 * * * /home/ubuntu/ai-employee/deploy/backup_odoo.sh >> /home/ubuntu/backups/backup.log 2>&1
```

---

## Daily Operations

### Check Status

```bash
# All services
docker-compose -f docker-compose.cloud.yml ps

# Cloud agent logs
docker logs employee_cloud_agent --tail 50

# Health
curl http://localhost:9000/health
```

### Restart Services

```bash
# Restart everything
docker-compose -f docker-compose.cloud.yml restart

# Restart just the cloud agent
docker restart employee_cloud_agent
```

### Update Code

```bash
cd ~/ai-employee
git pull origin main
docker-compose -f deploy/docker-compose.cloud.yml up -d --build cloud_agent
```

### Manual Vault Sync

```bash
cd ~/ai-employee/vault
git pull --rebase origin main
git add -A && git commit -m "manual sync" && git push origin main
```

---

## Monitoring

The cloud agent writes health reports to `Updates/health_report.md` in the vault. The local agent reads these and sends WhatsApp alerts if something goes wrong.

### Health Endpoint

```
GET http://YOUR_VM_IP:9000/health
```

Returns:

```json
{
  "status": "healthy",
  "mode": "cloud",
  "managed_processes": ["cloud_orchestrator", "cloud_health_monitor"],
  "timestamp": "2026-03-03T20:00:00"
}
```

### What the Cloud Agent Does (Automatically)

1. Pulls vault changes from Git
2. Scans `Needs_Action/{email,social,accounting}` for tasks
3. Claims tasks atomically (prevents double-processing)
4. Creates draft files in `Pending_Approval/{email,social,accounting}`
5. Writes status updates to `Updates/`
6. Pushes vault changes to Git
7. Repeats every 30 seconds

### What It Does NOT Do

- Send emails (creates drafts only)
- Post to social media (creates drafts only)
- Confirm invoices or register payments (creates drafts only)
- Access WhatsApp or banking credentials

---

## Troubleshooting

### Container won't start

```bash
docker-compose -f docker-compose.cloud.yml logs cloud_agent
```

### Odoo database error

```bash
# Reset and recreate
docker-compose -f docker-compose.cloud.yml down -v
docker-compose -f docker-compose.cloud.yml up -d
```

### Vault sync not working

```bash
# Test SSH to GitHub
ssh -T git@github.com

# Check vault remote
cd ~/ai-employee/vault
git remote -v
git pull origin main
```

### Out of disk space

```bash
# Clean Docker
docker system prune -a

# Check disk
df -h
```

---

## Architecture Diagram

```
  LOCAL (Windows)                           CLOUD (Oracle VM)
 +-----------------+                      +-------------------+
 | Local Agent     |                      | Cloud Agent       |
 | - Approvals     |   Git Vault Sync     | - Email triage    |
 | - WhatsApp      | <==================> | - Social drafts   |
 | - Send/Post     |                      | - Accounting read |
 | - Payments      |                      | - Health monitor  |
 +-----------------+                      +-------------------+
                                          | Odoo + PostgreSQL |
                                          | Nginx (HTTPS)     |
                                          +-------------------+
```

---

## Cost

| Service | Monthly Cost |
|---------|-------------|
| Oracle Cloud VM (Free Tier) | $0 |
| Domain name (optional) | ~$12/year |
| Let's Encrypt SSL | $0 |
| **Total** | **$0 - $1/month** |
